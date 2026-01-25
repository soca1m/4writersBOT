"""
ZeroGPT API Client (Free)
Provides AI detection using free ZeroGPT API endpoint
No API key required
"""
import logging
from typing import Dict, Any, List
import httpx

logger = logging.getLogger(__name__)


class ZeroGPT:
    """Client for free ZeroGPT API - AI detection without API key"""

    def __init__(self):
        """Initialize ZeroGPT client - no API key needed"""
        self.base_url = "https://api.zerogpt.com"
        self.headers = {
            'Host': 'api.zerogpt.com',
            'Connection': 'keep-alive',
            'sec-ch-ua-platform': '"Windows"',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'sec-ch-ua': '"Chromium";v="141", "Not?A_Brand";v="8"',
            'sec-ch-ua-mobile': '?0',
            'Origin': 'https://www.zerogpt.com',
            'Sec-Fetch-Site': 'same-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://www.zerogpt.com/',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json'
        }
        # Optional cookies for better reliability
        self.cookies = {
            '_gcl_au': '1.1.1742589142.1769198399',
            '_ga': 'GA1.1.1608941688.1769198399',
            '_ga_0YHYR2F422': 'GS2.1.s1769198399$o1$g0$t1769198399$j60$l0$h1972037899'
        }

    async def detect_ai(self, text: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Detect AI-generated content using free ZeroGPT API

        Args:
            text: Text to analyze
            timeout: Request timeout in seconds

        Returns:
            Dict with:
                - success: bool
                - ai_percentage: Percentage of AI content (0-100)
                - is_human: 0 if AI, higher values for human
                - feedback: Human-readable result
                - ai_words: Number of AI-detected words
                - total_words: Total word count
                - error: Error message if failed
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info("Submitting text to ZeroGPT (free API)...")

                response = await client.post(
                    f"{self.base_url}/api/detect/detectText",
                    headers=self.headers,
                    cookies=self.cookies,
                    json={"input_text": text}
                )

                if response.status_code != 200:
                    logger.error(f"ZeroGPT API error: {response.status_code}")
                    return {
                        "success": False,
                        "error": f"API error {response.status_code}",
                        "ai_percentage": 0,
                        "is_human": 100
                    }

                data = response.json()

                if not data.get("success"):
                    logger.error(f"ZeroGPT detection failed: {data.get('message', 'Unknown error')}")
                    return {
                        "success": False,
                        "error": data.get("message", "Detection failed"),
                        "ai_percentage": 0,
                        "is_human": 100
                    }

                result = data.get("data", {})

                # Extract key metrics
                ai_percentage = result.get("fakePercentage", 0)
                is_human = result.get("isHuman", 0)
                ai_words = result.get("aiWords", 0)
                total_words = result.get("textWords", 0)
                feedback = result.get("feedback", "")

                # Get sentences marked as human vs AI
                human_sentences = result.get("h", [])  # Human sentences
                ai_sentences = result.get("hi", [])    # AI sentences (usually empty if all AI)

                logger.info(f"ZeroGPT detection complete: {ai_percentage:.1f}% AI")

                return {
                    "success": True,
                    "error": None,
                    "ai_percentage": ai_percentage,
                    "is_human": is_human,
                    "feedback": feedback,
                    "ai_words": ai_words,
                    "total_words": total_words,
                    "human_sentences": human_sentences,
                    "ai_sentences": ai_sentences,
                    "raw_data": result
                }

        except Exception as e:
            logger.error(f"ZeroGPT error: {e}")
            return {
                "success": False,
                "error": str(e),
                "ai_percentage": 0,
                "is_human": 100
            }

    def interpret_result(self, ai_percentage: float) -> str:
        """
        Interpret AI detection result

        Args:
            ai_percentage: AI percentage (0-100)

        Returns:
            Human-readable interpretation
        """
        if ai_percentage < 20:
            return "Definitely human-written"
        elif ai_percentage < 50:
            return "Mostly human with some AI assistance"
        elif ai_percentage < 80:
            return "Mixed human and AI content"
        elif ai_percentage < 95:
            return "Mostly AI-generated"
        else:
            return "Completely AI-generated"


async def test_zerogpt():
    """Test ZeroGPT free API"""

    test_text = """
    Artificial intelligence has revolutionized numerous industries by providing innovative
    solutions to complex problems. Machine learning algorithms can process vast amounts of
    data and identify patterns that would be impossible for humans to detect manually.
    This technology has applications in healthcare, finance, transportation, and many other
    sectors. As AI continues to evolve, it promises to bring even more transformative
    changes to our daily lives and work environments.
    """

    print("=" * 80)
    print("TESTING ZEROGPT (FREE API)")
    print("=" * 80)
    print(f"\nText length: {len(test_text.split())} words\n")

    client = ZeroGPT()
    result = await client.detect_ai(test_text)

    if result.get("success"):
        print(f"✅ Detection successful!")
        print(f"   AI Percentage: {result.get('ai_percentage', 0):.1f}%")
        print(f"   Is Human: {result.get('is_human', 0)}")
        print(f"   AI Words: {result.get('ai_words', 0)}/{result.get('total_words', 0)}")
        print(f"   Feedback: {result.get('feedback', '')}")
        print(f"   Interpretation: {client.interpret_result(result.get('ai_percentage', 0))}")
    else:
        print(f"❌ Detection failed: {result.get('error')}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_zerogpt())