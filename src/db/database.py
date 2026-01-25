"""
SQLite database for storing user settings, workflows, and execution details
"""
import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_FILE = Path(__file__).parent.parent.parent / "data" / "bot.db"


def _ensure_data_dir():
    """Ensure data directory exists"""
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db():
    """Get database connection context manager"""
    _ensure_data_dir()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Initialize database tables"""
    _ensure_data_dir()

    with get_db() as conn:
        cursor = conn.cursor()

        # User settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                chat_id INTEGER PRIMARY KEY,
                auto_collect_enabled BOOLEAN DEFAULT 0,
                max_orders INTEGER DEFAULT 4,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Order criteria table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_criteria (
                chat_id INTEGER PRIMARY KEY,
                min_price REAL,
                max_price REAL,
                order_types TEXT,  -- JSON array
                academic_levels TEXT,  -- JSON array
                subjects TEXT,  -- JSON array
                min_pages INTEGER,
                max_pages INTEGER,
                min_deadline_hours INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES user_settings(chat_id)
            )
        """)

        # Workflows table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                order_id TEXT NOT NULL,
                order_index INTEGER,
                status TEXT NOT NULL,  -- pending, running, completed, failed
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                error TEXT,
                final_text TEXT,
                word_count INTEGER,
                ai_score REAL,
                FOREIGN KEY (chat_id) REFERENCES user_settings(chat_id)
            )
        """)

        # Workflow stages table (detailed step-by-step execution log)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER NOT NULL,
                stage_name TEXT NOT NULL,  -- e.g. "requirements_analysis", "research", "writing"
                status TEXT NOT NULL,  -- pending, in_progress, completed, failed
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                input_data TEXT,  -- JSON
                output_data TEXT,  -- JSON
                error TEXT,
                agent_logs TEXT,  -- JSON array of log messages
                FOREIGN KEY (workflow_id) REFERENCES workflows(id)
            )
        """)

        # Workflow statistics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_stats (
                chat_id INTEGER PRIMARY KEY,
                total_workflows INTEGER DEFAULT 0,
                completed_workflows INTEGER DEFAULT 0,
                failed_workflows INTEGER DEFAULT 0,
                total_words_generated INTEGER DEFAULT 0,
                avg_ai_score REAL DEFAULT 0.0,
                last_workflow_at TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES user_settings(chat_id)
            )
        """)

        # Create indexes for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflows_chat_id
            ON workflows(chat_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflows_status
            ON workflows(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflow_stages_workflow_id
            ON workflow_stages(workflow_id)
        """)

        conn.commit()
        logger.info("✅ Database initialized successfully")


# ==================== USER SETTINGS ====================

def get_user_settings(chat_id: int) -> Dict[str, Any]:
    """Get user settings"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Get main settings
        cursor.execute("""
            SELECT auto_collect_enabled, max_orders
            FROM user_settings
            WHERE chat_id = ?
        """, (chat_id,))

        row = cursor.fetchone()

        if not row:
            # Create default settings
            cursor.execute("""
                INSERT INTO user_settings (chat_id, auto_collect_enabled, max_orders)
                VALUES (?, 0, 4)
            """, (chat_id,))
            conn.commit()

            return {
                "auto_collect_enabled": False,
                "max_orders": 4,
                "criteria": {}
            }

        # Get criteria
        cursor.execute("""
            SELECT min_price, max_price, order_types, academic_levels,
                   subjects, min_pages, max_pages, min_deadline_hours
            FROM order_criteria
            WHERE chat_id = ?
        """, (chat_id,))

        criteria_row = cursor.fetchone()

        criteria = {}
        if criteria_row:
            criteria = {
                "min_price": criteria_row["min_price"],
                "max_price": criteria_row["max_price"],
                "order_types": json.loads(criteria_row["order_types"]) if criteria_row["order_types"] else [],
                "academic_levels": json.loads(criteria_row["academic_levels"]) if criteria_row["academic_levels"] else [],
                "subjects": json.loads(criteria_row["subjects"]) if criteria_row["subjects"] else [],
                "min_pages": criteria_row["min_pages"],
                "max_pages": criteria_row["max_pages"],
                "min_deadline_hours": criteria_row["min_deadline_hours"],
            }

        return {
            "auto_collect_enabled": bool(row["auto_collect_enabled"]),
            "max_orders": row["max_orders"],
            "criteria": criteria
        }


def update_user_settings(chat_id: int, updates: Dict[str, Any]):
    """Update user settings"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Ensure user exists
        cursor.execute("SELECT 1 FROM user_settings WHERE chat_id = ?", (chat_id,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO user_settings (chat_id) VALUES (?)
            """, (chat_id,))

        # Update fields
        set_clauses = []
        values = []

        if "auto_collect_enabled" in updates:
            set_clauses.append("auto_collect_enabled = ?")
            values.append(int(updates["auto_collect_enabled"]))

        if "max_orders" in updates:
            set_clauses.append("max_orders = ?")
            values.append(updates["max_orders"])

        if set_clauses:
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(chat_id)

            query = f"UPDATE user_settings SET {', '.join(set_clauses)} WHERE chat_id = ?"
            cursor.execute(query, values)

        conn.commit()
        logger.info(f"Updated settings for chat {chat_id}")


def update_criteria(chat_id: int, criteria_updates: Dict[str, Any]):
    """Update order criteria"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if criteria exists
        cursor.execute("SELECT 1 FROM order_criteria WHERE chat_id = ?", (chat_id,))
        exists = cursor.fetchone()

        if not exists:
            # Insert default
            cursor.execute("""
                INSERT INTO order_criteria (chat_id) VALUES (?)
            """, (chat_id,))

        # Prepare update
        set_clauses = []
        values = []

        field_mapping = {
            "min_price": "min_price",
            "max_price": "max_price",
            "order_types": "order_types",
            "academic_levels": "academic_levels",
            "subjects": "subjects",
            "min_pages": "min_pages",
            "max_pages": "max_pages",
            "min_deadline_hours": "min_deadline_hours"
        }

        for key, db_field in field_mapping.items():
            if key in criteria_updates:
                set_clauses.append(f"{db_field} = ?")

                # JSON encode arrays
                if key in ["order_types", "academic_levels", "subjects"]:
                    values.append(json.dumps(criteria_updates[key]))
                else:
                    values.append(criteria_updates[key])

        if set_clauses:
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(chat_id)

            query = f"UPDATE order_criteria SET {', '.join(set_clauses)} WHERE chat_id = ?"
            cursor.execute(query, values)

        conn.commit()
        logger.info(f"Updated criteria for chat {chat_id}: {criteria_updates}")


def toggle_auto_collect(chat_id: int) -> bool:
    """Toggle auto-collection on/off"""
    settings = get_user_settings(chat_id)
    new_state = not settings["auto_collect_enabled"]
    update_user_settings(chat_id, {"auto_collect_enabled": new_state})
    return new_state


# ==================== WORKFLOWS ====================

def create_workflow(chat_id: int, order_id: str, order_index: Optional[int] = None) -> int:
    """
    Create new workflow record

    Returns:
        workflow_id
    """
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO workflows (chat_id, order_id, order_index, status)
            VALUES (?, ?, ?, 'pending')
        """, (chat_id, order_id, order_index))

        workflow_id = cursor.lastrowid

        # Update stats
        cursor.execute("""
            INSERT INTO workflow_stats (chat_id, total_workflows, last_workflow_at)
            VALUES (?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(chat_id) DO UPDATE SET
                total_workflows = total_workflows + 1,
                last_workflow_at = CURRENT_TIMESTAMP
        """, (chat_id,))

        conn.commit()
        logger.info(f"Created workflow {workflow_id} for order {order_id}")

        return workflow_id


def update_workflow_status(workflow_id: int, status: str, **kwargs):
    """
    Update workflow status

    Args:
        workflow_id: Workflow ID
        status: New status (running, completed, failed)
        **kwargs: Optional fields (error, final_text, word_count, ai_score)
    """
    with get_db() as conn:
        cursor = conn.cursor()

        set_clauses = ["status = ?"]
        values = [status]

        if status in ["completed", "failed"]:
            set_clauses.append("completed_at = CURRENT_TIMESTAMP")

        if "error" in kwargs:
            set_clauses.append("error = ?")
            values.append(kwargs["error"])

        if "final_text" in kwargs:
            set_clauses.append("final_text = ?")
            values.append(kwargs["final_text"])

        if "word_count" in kwargs:
            set_clauses.append("word_count = ?")
            values.append(kwargs["word_count"])

        if "ai_score" in kwargs:
            set_clauses.append("ai_score = ?")
            values.append(kwargs["ai_score"])

        values.append(workflow_id)

        query = f"UPDATE workflows SET {', '.join(set_clauses)} WHERE id = ?"
        cursor.execute(query, values)

        # Update stats
        if status == "completed":
            cursor.execute("""
                SELECT chat_id, word_count, ai_score FROM workflows WHERE id = ?
            """, (workflow_id,))
            row = cursor.fetchone()

            if row:
                chat_id = row["chat_id"]
                word_count = row["word_count"] or 0
                ai_score = row["ai_score"] or 0.0

                cursor.execute("""
                    UPDATE workflow_stats SET
                        completed_workflows = completed_workflows + 1,
                        total_words_generated = total_words_generated + ?,
                        avg_ai_score = (avg_ai_score * completed_workflows + ?) / (completed_workflows + 1)
                    WHERE chat_id = ?
                """, (word_count, ai_score, chat_id))

        elif status == "failed":
            cursor.execute("""
                SELECT chat_id FROM workflows WHERE id = ?
            """, (workflow_id,))
            row = cursor.fetchone()

            if row:
                cursor.execute("""
                    UPDATE workflow_stats SET
                        failed_workflows = failed_workflows + 1
                    WHERE chat_id = ?
                """, (row["chat_id"],))

        conn.commit()
        logger.info(f"Updated workflow {workflow_id} status to {status}")


def add_workflow_stage(
    workflow_id: int,
    stage_name: str,
    status: str = "pending",
    input_data: Optional[Dict] = None,
    output_data: Optional[Dict] = None,
    error: Optional[str] = None,
    agent_logs: Optional[List[str]] = None
) -> int:
    """
    Add workflow stage record

    Returns:
        stage_id
    """
    with get_db() as conn:
        cursor = conn.cursor()

        started_at = datetime.now().isoformat() if status != "pending" else None
        completed_at = datetime.now().isoformat() if status in ["completed", "failed"] else None

        cursor.execute("""
            INSERT INTO workflow_stages
            (workflow_id, stage_name, status, started_at, completed_at,
             input_data, output_data, error, agent_logs)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            workflow_id,
            stage_name,
            status,
            started_at,
            completed_at,
            json.dumps(input_data) if input_data else None,
            json.dumps(output_data) if output_data else None,
            error,
            json.dumps(agent_logs) if agent_logs else None
        ))

        stage_id = cursor.lastrowid
        conn.commit()

        return stage_id


def update_workflow_stage(
    stage_id: int,
    status: str,
    output_data: Optional[Dict] = None,
    error: Optional[str] = None,
    agent_logs: Optional[List[str]] = None
):
    """Update workflow stage"""
    with get_db() as conn:
        cursor = conn.cursor()

        set_clauses = ["status = ?"]
        values = [status]

        if status == "in_progress" and not cursor.execute(
            "SELECT started_at FROM workflow_stages WHERE id = ?", (stage_id,)
        ).fetchone()["started_at"]:
            set_clauses.append("started_at = CURRENT_TIMESTAMP")

        if status in ["completed", "failed"]:
            set_clauses.append("completed_at = CURRENT_TIMESTAMP")

        if output_data:
            set_clauses.append("output_data = ?")
            values.append(json.dumps(output_data))

        if error:
            set_clauses.append("error = ?")
            values.append(error)

        if agent_logs:
            set_clauses.append("agent_logs = ?")
            values.append(json.dumps(agent_logs))

        values.append(stage_id)

        query = f"UPDATE workflow_stages SET {', '.join(set_clauses)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()


def get_workflow_stats(chat_id: int) -> Dict[str, Any]:
    """Get workflow statistics for user"""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT total_workflows, completed_workflows, failed_workflows,
                   total_words_generated, avg_ai_score, last_workflow_at
            FROM workflow_stats
            WHERE chat_id = ?
        """, (chat_id,))

        row = cursor.fetchone()

        if not row:
            return {
                "total_workflows": 0,
                "completed_workflows": 0,
                "failed_workflows": 0,
                "total_words_generated": 0,
                "avg_ai_score": 0.0,
                "last_workflow_at": None
            }

        return dict(row)


def get_workflows_by_status(chat_id: int, status: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get workflows by status"""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, order_id, order_index, status, started_at, completed_at,
                   word_count, ai_score, error
            FROM workflows
            WHERE chat_id = ? AND status = ?
            ORDER BY started_at DESC
            LIMIT ?
        """, (chat_id, status, limit))

        return [dict(row) for row in cursor.fetchall()]


def get_workflow_details(workflow_id: int) -> Optional[Dict[str, Any]]:
    """Get full workflow details including stages"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Get workflow
        cursor.execute("""
            SELECT id, chat_id, order_id, order_index, status, started_at,
                   completed_at, error, final_text, word_count, ai_score
            FROM workflows
            WHERE id = ?
        """, (workflow_id,))

        workflow_row = cursor.fetchone()

        if not workflow_row:
            return None

        workflow = dict(workflow_row)

        # Get stages
        cursor.execute("""
            SELECT id, stage_name, status, started_at, completed_at,
                   input_data, output_data, error, agent_logs
            FROM workflow_stages
            WHERE workflow_id = ?
            ORDER BY id ASC
        """, (workflow_id,))

        stages = []
        for stage_row in cursor.fetchall():
            stage = dict(stage_row)

            # Parse JSON fields
            if stage["input_data"]:
                stage["input_data"] = json.loads(stage["input_data"])
            if stage["output_data"]:
                stage["output_data"] = json.loads(stage["output_data"])
            if stage["agent_logs"]:
                stage["agent_logs"] = json.loads(stage["agent_logs"])

            stages.append(stage)

        workflow["stages"] = stages

        return workflow
