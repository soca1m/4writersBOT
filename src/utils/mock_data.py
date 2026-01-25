"""
Mock data for testing without real API calls
"""
from py4writers import Order
from typing import List


def get_mock_orders() -> List[Order]:
    """Get mock available orders"""
    return [
        Order(
            title="[4W] Impact of Social Media on Mental Health",
            subject="Psychology",
            order_id="9700832761",
            order_index=101,
            description="Analyze the psychological effects of social media usage on teenagers",
            deadline="2026-01-25 14:00:00",
            remaining="Time remaining: 1d 12h 30m",
            order_type="Essay",
            academic_level="College",
            style="APA",
            language="English",
            pages=3,
            sources=5,
            salary=12.0,
            bonus=3.0,
            total=15.0
        ),
        Order(
            title="[4W] Climate Change and Global Economics",
            subject="Economics",
            order_id="9700832762",
            order_index=102,
            description="Discuss economic impacts of climate change",
            deadline="2026-01-26 10:00:00",
            remaining="Time remaining: 2d 8h 15m",
            order_type="Research Paper",
            academic_level="Master",
            style="APA",
            language="English",
            pages=5,
            sources=10,
            salary=20.0,
            bonus=5.0,
            total=25.0
        ),
        Order(
            title="[4W] Nursing Ethics Case Study",
            subject="Nursing",
            order_id="9700832763",
            order_index=103,
            description="Ethical dilemmas in patient care",
            deadline="2026-01-24 20:00:00",
            remaining="Time remaining: 0d 18h 45m",
            order_type="Case Study",
            academic_level="College",
            style="APA",
            language="English",
            pages=2,
            sources=4,
            salary=8.0,
            bonus=2.0,
            total=10.0
        ),
        Order(
            title="[4W] Machine Learning Applications",
            subject="Computer Science",
            order_id="9700832764",
            order_index=104,
            description="Overview of ML in healthcare",
            deadline="2026-01-27 16:00:00",
            remaining="Time remaining: 3d 14h 20m",
            order_type="Discussion Board Post",
            academic_level="Undergraduate",
            style="APA",
            language="English",
            pages=1,
            sources=3,
            salary=4.0,
            bonus=1.0,
            total=5.0
        ),
        Order(
            title="[4W] Roman Empire Historical Analysis",
            subject="History",
            order_id="9700832765",
            order_index=105,
            description="Fall of the Roman Empire causes",
            deadline="2026-01-28 12:00:00",
            remaining="Time remaining: 4d 10h 0m",
            order_type="Essay",
            academic_level="High School",
            style="MLA",
            language="English",
            pages=4,
            sources=7,
            salary=16.0,
            bonus=4.0,
            total=20.0
        )
    ]


def get_mock_processing_orders() -> List[Order]:
    """Get mock processing/active orders"""
    return [
        Order(
            title="[4W] Shakespeare Literature Review",
            subject="Literature",
            order_id="9700832750",
            order_index=90,
            description="Analysis of Hamlet themes",
            deadline="2026-01-25 18:00:00",
            remaining="Time remaining: 1d 16h 30m",
            order_type="Essay",
            academic_level="College",
            style="MLA",
            language="English",
            pages=3,
            sources=5,
            salary=12.0,
            bonus=3.0,
            total=15.0
        ),
        Order(
            title="[4W] Database Design Project",
            subject="Computer Science",
            order_id="9700832751",
            order_index=91,
            description="Design ER diagram for e-commerce",
            deadline="2026-01-26 14:00:00",
            remaining="Time remaining: 2d 12h 15m",
            order_type="Coursework",
            academic_level="Undergraduate",
            style="APA",
            language="English",
            pages=2,
            sources=3,
            salary=8.0,
            bonus=2.0,
            total=10.0
        )
    ]


def get_mock_completed_orders() -> List[Order]:
    """Get mock completed orders"""
    return [
        Order(
            title="[4W] COVID-19 Pandemic Analysis",
            subject="Medicine",
            order_id="9700832740",
            order_index=80,
            description="Healthcare system response",
            deadline="2026-01-20 10:00:00",
            remaining="Time remaining: 0d 0h 0m",
            order_type="Research Paper",
            academic_level="Master",
            style="APA",
            language="English",
            pages=6,
            sources=12,
            salary=24.0,
            bonus=6.0,
            total=30.0
        ),
        Order(
            title="[4W] Marketing Strategy Analysis",
            subject="Business",
            order_id="9700832741",
            order_index=81,
            description="Digital marketing trends 2024",
            deadline="2026-01-21 14:00:00",
            remaining="Time remaining: 0d 0h 0m",
            order_type="Essay",
            academic_level="College",
            style="APA",
            language="English",
            pages=4,
            sources=8,
            salary=16.0,
            bonus=4.0,
            total=20.0
        ),
        Order(
            title="[4W] Environmental Science Report",
            subject="Environmental Science",
            order_id="9700832742",
            order_index=82,
            description="Water pollution effects",
            deadline="2026-01-22 16:00:00",
            remaining="Time remaining: 0d 0h 0m",
            order_type="Case Study",
            academic_level="College",
            style="APA",
            language="English",
            pages=3,
            sources=6,
            salary=12.0,
            bonus=3.0,
            total=15.0
        ),
        Order(
            title="[4W] Philosophy Ethics Discussion",
            subject="Philosophy",
            order_id="9700832743",
            order_index=83,
            description="Utilitarianism vs Deontology",
            deadline="2026-01-19 12:00:00",
            remaining="Time remaining: 0d 0h 0m",
            order_type="Discussion Board Post",
            academic_level="College",
            style="MLA",
            language="English",
            pages=1,
            sources=3,
            salary=4.0,
            bonus=1.0,
            total=5.0
        ),
        Order(
            title="[4W] Artificial Intelligence Future",
            subject="Computer Science",
            order_id="9700832744",
            order_index=84,
            description="AI impact on employment",
            deadline="2026-01-18 10:00:00",
            remaining="Time remaining: 0d 0h 0m",
            order_type="Essay",
            academic_level="Undergraduate",
            style="APA",
            language="English",
            pages=5,
            sources=10,
            salary=20.0,
            bonus=5.0,
            total=25.0
        ),
        Order(
            title="[4W] Quantum Physics Fundamentals",
            subject="Physics",
            order_id="9700832745",
            order_index=85,
            description="Introduction to quantum mechanics",
            deadline="2026-01-17 14:00:00",
            remaining="Time remaining: 0d 0h 0m",
            order_type="Research Paper",
            academic_level="Master",
            style="APA",
            language="English",
            pages=7,
            sources=15,
            salary=28.0,
            bonus=7.0,
            total=35.0
        ),
        Order(
            title="[4W] Sociology Urban Development",
            subject="Sociology",
            order_id="9700832746",
            order_index=86,
            description="Gentrification effects",
            deadline="2026-01-16 16:00:00",
            remaining="Time remaining: 0d 0h 0m",
            order_type="Essay",
            academic_level="College",
            style="APA",
            language="English",
            pages=4,
            sources=7,
            salary=16.0,
            bonus=4.0,
            total=20.0
        ),
        Order(
            title="[4W] Biology Cell Structure",
            subject="Biology",
            order_id="9700832747",
            order_index=87,
            description="Eukaryotic vs Prokaryotic cells",
            deadline="2026-01-15 12:00:00",
            remaining="Time remaining: 0d 0h 0m",
            order_type="Coursework",
            academic_level="High School",
            style="APA",
            language="English",
            pages=2,
            sources=4,
            salary=8.0,
            bonus=2.0,
            total=10.0
        )
    ]


def get_mock_late_orders() -> List[Order]:
    """Get mock late orders"""
    return [
        Order(
            title="[4W] Urgent History Assignment",
            subject="History",
            order_id="9700832730",
            order_index=70,
            description="World War II analysis",
            deadline="2026-01-23 10:00:00",
            remaining="Time remaining: -1d 2h 0m",
            order_type="Essay",
            academic_level="College",
            style="MLA",
            language="English",
            pages=3,
            sources=5,
            salary=12.0,
            bonus=3.0,
            total=15.0
        )
    ]


def get_mock_revision_orders() -> List[Order]:
    """Get mock revision orders"""
    return [
        Order(
            title="[4W] Chemistry Lab Report Revision",
            subject="Chemistry",
            order_id="9700832720",
            order_index=60,
            description="Fix calculations and formatting",
            deadline="2026-01-25 12:00:00",
            remaining="Time remaining: 1d 10h 30m",
            order_type="Coursework",
            academic_level="College",
            style="APA",
            language="English",
            pages=2,
            sources=3,
            salary=6.0,
            bonus=1.5,
            total=7.5
        )
    ]
