"""
Undetectable AI API Client
Provides AI detection and humanization using Undetectable.AI API
"""
import asyncio
import logging
import os
from typing import Dict, Any, Optional, Literal, List
import httpx

logger = logging.getLogger(__name__)

# Type definitions for humanization parameters
ReadabilityLevel = Literal["High School", "University", "Doctorate", "Journalist", "Marketing"]
PurposeType = Literal["General Writing", "Essay", "Article", "Marketing Material", "Story",
                      "Cover Letter", "Report", "Business Material", "Legal Material"]
StrengthLevel = Literal["Quality", "Balanced", "More Human"]
ModelVersion = Literal["v2", "v11", "v11sr"]


class UndetectableAI:
    """Client for Undetectable.AI API - AI detection and humanization"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Undetectable AI client

        Args:
            api_key: API key (defaults to UNDETECTABLE_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("UNDETECTABLE_API_KEY")
        self.detect_base_url = "https://ai-detect.undetectable.ai"
        self.humanize_base_url = "https://humanize.undetectable.ai"

        if not self.api_key:
            logger.warning("UNDETECTABLE_API_KEY not set")

    # ==================== DETECTION METHODS ====================

    async def detect_ai(
        self,
        text: str,
        model: str = "xlm_ud_detector",
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Detect AI-generated content in text

        Args:
            text: Text to analyze (recommended min 200 words)
            model: Detection model to use (default: xlm_ud_detector)
            timeout: Max time to wait for result (seconds)

        Returns:
            Dict with:
                - success: bool
                - result: AI score (1-100, <50=human, 50-60=possible AI, >60=AI)
                - result_details: Scores from individual detectors
                - error: Error message if failed

        Threshold:
            - Under 50: Definitely human
            - 50-60: Possible AI
            - Over 60: Definite AI (99%+ accuracy)
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "API key not set",
                "result": None,
                "result_details": None
            }

        if len(text.split()) < 200:
            logger.warning("Text under 200 words - detection accuracy may be lower")

        if len(text.split()) > 30000:
            logger.error("Text exceeds 30,000 word limit")
            return {
                "success": False,
                "error": "Text exceeds 30,000 word limit",
                "result": None,
                "result_details": None
            }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Submit text for detection
                logger.info("Submitting text for AI detection...")
                submit_response = await client.post(
                    f"{self.detect_base_url}/detect",
                    headers={
                        "accept": "application/json",
                        "Content-Type": "application/json"
                    },
                    json={
                        "text": text,
                        "key": self.api_key,
                        "model": model,
                        "retry_count": 0
                    }
                )

                if submit_response.status_code != 200:
                    logger.error(f"Detection submission failed: {submit_response.status_code}")
                    return {
                        "success": False,
                        "error": f"API error {submit_response.status_code}",
                        "result": None,
                        "result_details": None
                    }

                submit_data = submit_response.json()
                document_id = submit_data.get("id")

                if not document_id:
                    logger.error("No document ID received")
                    return {
                        "success": False,
                        "error": "No document ID received",
                        "result": None,
                        "result_details": None
                    }

                logger.info(f"Document submitted, ID: {document_id}")
                logger.info("Polling for results (2-4 seconds expected)...")

                # Poll for results (average 2-4 seconds)
                max_polls = timeout
                poll_interval = 1  # seconds

                for attempt in range(max_polls):
                    await asyncio.sleep(poll_interval)

                    query_response = await client.post(
                        f"{self.detect_base_url}/query",
                        headers={
                            "accept": "application/json",
                            "Content-Type": "application/json"
                        },
                        json={"id": document_id}
                    )

                    if query_response.status_code != 200:
                        logger.error(f"Query failed: {query_response.status_code}")
                        continue

                    query_data = query_response.json()
                    status = query_data.get("status")

                    if status == "done":
                        logger.info("Detection complete")
                        return {
                            "success": True,
                            "error": None,
                            "result": query_data.get("result"),
                            "result_details": query_data.get("result_details", {}),
                            "model": query_data.get("model")
                        }
                    elif status == "pending":
                        logger.debug(f"Still pending... ({attempt + 1}/{max_polls})")
                        continue
                    else:
                        logger.error(f"Unexpected status: {status}")
                        return {
                            "success": False,
                            "error": f"Unexpected status: {status}",
                            "result": None,
                            "result_details": None
                        }

                # Timeout
                logger.error("Detection timeout")
                return {
                    "success": False,
                    "error": "Detection timeout",
                    "result": None,
                    "result_details": None
                }

        except Exception as e:
            logger.error(f"Detection error: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": None,
                "result_details": None
            }

    def interpret_result(self, result: float) -> str:
        """
        Interpret AI detection result

        Args:
            result: AI score (1-100)

        Returns:
            Human-readable interpretation
        """
        if result < 50:
            return "Definitely human"
        elif result < 60:
            return "Possibly AI-generated"
        else:
            return "Definitely AI-generated"

    # ==================== HUMANIZATION METHODS ====================

    async def humanize(
        self,
        text: str,
        readability: ReadabilityLevel = "University",
        purpose: PurposeType = "Essay",
        strength: StrengthLevel = "Balanced",
        model: ModelVersion = "v11",
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        Humanize AI-generated text to bypass AI detectors

        Args:
            text: Text to humanize (min 50 chars)
            readability: Target reading level
            purpose: Type of content
            strength: Aggressiveness of humanization
                - "Quality": Light touch, preserves meaning
                - "Balanced": Default, good balance
                - "More Human": Aggressive, most human-like
            model: Model version
                - "v2": Supports all languages, medium humanization
                - "v11": Best for English, high humanization
                - "v11sr": Slightly slower, best for English, best humanization
            timeout: Max time to wait for result (seconds)

        Returns:
            Dict with:
                - success: bool
                - output: Humanized text
                - input: Original text
                - document_id: Document ID for future reference
                - error: Error message if failed
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "API key not set",
                "output": None,
                "input": text
            }

        if len(text) < 50:
            logger.error("Text must be at least 50 characters")
            return {
                "success": False,
                "error": "Text must be at least 50 characters",
                "output": None,
                "input": text
            }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Submit text for humanization
                logger.info(f"Submitting text for humanization (model={model}, strength={strength})...")
                submit_response = await client.post(
                    f"{self.humanize_base_url}/submit",
                    headers={
                        "apikey": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "content": text,
                        "readability": readability,
                        "purpose": purpose,
                        "strength": strength,
                        "model": model
                    }
                )

                if submit_response.status_code == 402:
                    logger.error("Insufficient credits for humanization")
                    return {
                        "success": False,
                        "error": "Insufficient credits",
                        "output": None,
                        "input": text
                    }

                if submit_response.status_code != 200:
                    logger.error(f"Humanization submission failed: {submit_response.status_code}")
                    error_text = submit_response.text
                    return {
                        "success": False,
                        "error": f"API error {submit_response.status_code}: {error_text}",
                        "output": None,
                        "input": text
                    }

                submit_data = submit_response.json()
                document_id = submit_data.get("id")

                if not document_id:
                    logger.error("No document ID received")
                    return {
                        "success": False,
                        "error": "No document ID received",
                        "output": None,
                        "input": text
                    }

                logger.info(f"Document submitted for humanization, ID: {document_id}")
                logger.info("Polling for results (may take 10-60 seconds depending on length)...")

                # Poll for results (5-10 second intervals as recommended)
                max_polls = timeout // 5
                poll_interval = 5  # seconds

                for attempt in range(max_polls):
                    await asyncio.sleep(poll_interval)

                    doc_response = await client.post(
                        f"{self.humanize_base_url}/document",
                        headers={
                            "apikey": self.api_key,
                            "Content-Type": "application/json"
                        },
                        json={"id": document_id}
                    )

                    if doc_response.status_code != 200:
                        logger.error(f"Document query failed: {doc_response.status_code}")
                        continue

                    doc_data = doc_response.json()

                    # Check if output is available
                    if doc_data.get("output"):
                        logger.info("Humanization complete")
                        return {
                            "success": True,
                            "error": None,
                            "output": doc_data.get("output"),
                            "input": doc_data.get("input"),
                            "document_id": document_id,
                            "readability": doc_data.get("readability"),
                            "purpose": doc_data.get("purpose")
                        }
                    else:
                        logger.debug(f"Still processing... ({attempt + 1}/{max_polls})")

                # Timeout
                logger.error("Humanization timeout")
                return {
                    "success": False,
                    "error": "Humanization timeout",
                    "output": None,
                    "input": text
                }

        except Exception as e:
            logger.error(f"Humanization error: {e}")
            return {
                "success": False,
                "error": str(e),
                "output": None,
                "input": text
            }

    async def rehumanize(self, document_id: str, timeout: int = 120) -> Dict[str, Any]:
        """
        Rehumanize a document (can be done once per document)

        Args:
            document_id: ID of previously humanized document
            timeout: Max time to wait for result (seconds)

        Returns:
            Dict with success status and new document ID
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "API key not set",
                "new_document_id": None
            }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.humanize_base_url}/rehumanize",
                    headers={
                        "apikey": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json={"id": document_id}
                )

                if response.status_code != 200:
                    logger.error(f"Rehumanization failed: {response.status_code}")
                    return {
                        "success": False,
                        "error": f"API error {response.status_code}",
                        "new_document_id": None
                    }

                data = response.json()
                new_id = data.get("id")

                logger.info(f"Rehumanization started, new ID: {new_id}")

                # Now poll for the result
                return await self.get_document(new_id, timeout)

        except Exception as e:
            logger.error(f"Rehumanization error: {e}")
            return {
                "success": False,
                "error": str(e),
                "new_document_id": None
            }

    async def get_document(self, document_id: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Retrieve a humanized document by ID

        Args:
            document_id: Document ID from humanization
            timeout: Max time to wait for result

        Returns:
            Dict with document data
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "API key not set"
            }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.humanize_base_url}/document",
                    headers={
                        "apikey": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json={"id": document_id}
                )

                if response.status_code != 200:
                    logger.error(f"Document retrieval failed: {response.status_code}")
                    return {
                        "success": False,
                        "error": f"API error {response.status_code}"
                    }

                data = response.json()
                return {
                    "success": True,
                    "error": None,
                    **data
                }

        except Exception as e:
            logger.error(f"Document retrieval error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def list_documents(self, offset: int = 0) -> Dict[str, Any]:
        """
        List humanized documents

        Args:
            offset: Pagination offset (returns 10 docs at a time)

        Returns:
            Dict with documents list and pagination info
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "API key not set",
                "documents": [],
                "pagination": False
            }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.humanize_base_url}/list",
                    headers={
                        "apikey": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json={"offset": offset} if offset > 0 else {}
                )

                if response.status_code != 200:
                    logger.error(f"Document list failed: {response.status_code}")
                    return {
                        "success": False,
                        "error": f"API error {response.status_code}",
                        "documents": [],
                        "pagination": False
                    }

                data = response.json()
                return {
                    "success": True,
                    "error": None,
                    "documents": data.get("documents", []),
                    "pagination": data.get("pagination", False)
                }

        except Exception as e:
            logger.error(f"Document list error: {e}")
            return {
                "success": False,
                "error": str(e),
                "documents": [],
                "pagination": False
            }

    async def check_credits(self) -> Dict[str, Any]:
        """
        Check user credit balance (works for both detection and humanization)

        Returns:
            Dict with:
                - success: bool
                - baseCredits: Base credits
                - boostCredits: Boost credits
                - credits: Total credits
                - error: Error message if failed
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "API key not set",
                "baseCredits": 0,
                "boostCredits": 0,
                "credits": 0
            }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Try humanization endpoint first (newer)
                response = await client.get(
                    f"{self.humanize_base_url}/check-user-credits",
                    headers={
                        "apikey": self.api_key,
                        "accept": "application/json",
                        "Content-Type": "application/json"
                    }
                )

                if response.status_code != 200:
                    # Fallback to detection endpoint
                    response = await client.get(
                        f"{self.detect_base_url}/check-user-credits",
                        headers={
                            "apikey": self.api_key,
                            "accept": "application/json",
                            "Content-Type": "application/json"
                        }
                    )

                if response.status_code != 200:
                    logger.error(f"Credit check failed: {response.status_code}")
                    return {
                        "success": False,
                        "error": f"API error {response.status_code}",
                        "baseCredits": 0,
                        "boostCredits": 0,
                        "credits": 0
                    }

                data = response.json()
                return {
                    "success": True,
                    "error": None,
                    "baseCredits": data.get("baseCredits", 0),
                    "boostCredits": data.get("boostCredits", 0),
                    "credits": data.get("credits", 0)
                }

        except Exception as e:
            logger.error(f"Credit check error: {e}")
            return {
                "success": False,
                "error": str(e),
                "baseCredits": 0,
                "boostCredits": 0,
                "credits": 0
            }

    # ==================== TEST METHODS ====================

    async def test_detection_and_humanization(self):
        """Test both detection and humanization capabilities"""

        test_text = """
        Artificial intelligence has revolutionized numerous industries by providing innovative
        solutions to complex problems. Machine learning algorithms can process vast amounts of
        data and identify patterns that would be impossible for humans to detect manually.
        This technology has applications in healthcare, finance, transportation, and many other
        sectors. As AI continues to evolve, it promises to bring even more transformative
        changes to our daily lives and work environments. The development of neural networks
        has been particularly significant in advancing AI capabilities. These systems can
        learn from experience and improve their performance over time.
        """

        print("=" * 80)
        print("TESTING UNDETECTABLE AI")
        print("=" * 80)

        # Check credits
        credits = await self.check_credits()
        if credits.get("success"):
            print(f"\n📊 Account Credits: {credits.get('credits', 0)}")
            print(f"   Base: {credits.get('baseCredits', 0)}")
            print(f"   Boost: {credits.get('boostCredits', 0)}")
        else:
            print(f"⚠️ Could not check credits: {credits.get('error')}")

        # Test detection
        print("\n" + "-" * 40)
        print("1. AI DETECTION")
        print("-" * 40)
        print(f"Text length: {len(test_text.split())} words")

        detection = await self.detect_ai(test_text)

        if detection.get("success"):
            ai_score = detection.get("result", 0)
            print(f"✅ Detection successful!")
            print(f"   AI Score: {ai_score:.1f}%")
            print(f"   Interpretation: {self.interpret_result(ai_score)}")

            details = detection.get("result_details", {})
            if details:
                print(f"\n   Detector breakdown:")
                for key, value in details.items():
                    if value is not None and key != "human":
                        print(f"   - {key}: {value:.1f}%")
        else:
            print(f"❌ Detection failed: {detection.get('error')}")
            return

        # Test humanization if detected as AI
        if ai_score > 60:
            print("\n" + "-" * 40)
            print("2. HUMANIZATION")
            print("-" * 40)
            print("Text detected as AI, testing humanization...")

            humanized = await self.humanize(
                test_text,
                readability="University",
                purpose="Essay",
                strength="Balanced",
                model="v11"
            )

            if humanized.get("success"):
                print(f"✅ Humanization successful!")
                print(f"   Document ID: {humanized.get('document_id')}")
                output = humanized.get("output", "")
                print(f"   Output preview: {output[:200]}...")

                # Test detection on humanized text
                print("\n" + "-" * 40)
                print("3. RE-DETECTION ON HUMANIZED TEXT")
                print("-" * 40)

                re_detection = await self.detect_ai(output)

                if re_detection.get("success"):
                    new_ai_score = re_detection.get("result", 0)
                    print(f"✅ Re-detection successful!")
                    print(f"   Original AI Score: {ai_score:.1f}%")
                    print(f"   New AI Score: {new_ai_score:.1f}%")
                    print(f"   Improvement: {ai_score - new_ai_score:.1f}% reduction")
                    print(f"   New interpretation: {self.interpret_result(new_ai_score)}")
                else:
                    print(f"❌ Re-detection failed: {re_detection.get('error')}")
            else:
                print(f"❌ Humanization failed: {humanized.get('error')}")
        else:
            print(f"\n✅ Text appears human (score: {ai_score:.1f}%), no humanization needed")


if __name__ == "__main__":
    # For testing
    import asyncio

    async def main():
        client = UndetectableAI()
        await client.test_detection_and_humanization()

    asyncio.run(main())