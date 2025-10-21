import os
import openai
import logging
from typing import Optional
import time

logger = logging.getLogger(__name__)

class GrokClient:
    def __init__(self):
        self.api_key = os.getenv("GROK_API_KEY")
        if not self.api_key:
            raise ValueError("GROK_API_KEY environment variable is required")
        
        # Configure OpenAI client for Grok
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"
        )
        
        self.model = os.getenv("GROK_MODEL", "grok-3")
        self.max_tokens = int(os.getenv("GROK_MAX_TOKENS", "1000"))
        self.temperature = float(os.getenv("GROK_TEMPERATURE", "0.9"))  # Higher for more variety

    def get_response(self, query: str, system_prompt: Optional[str] = None) -> str:
        """Get response from Grok AI"""
        try:
            messages = []
            
            # Use default snarky prompt if none provided
            if not system_prompt:
                system_prompt = f"Some Rando just pushed a button that called you. you are tired, and grumpy. Be a smartass comedian unhinged, always tell a fresh, snarky joke. Mix it up and be unpredictable! no Skeleton jokes! no  Ba-dum-tss. No dumb jokes, like elevators letting you down, etc. no time stamp! try and keep it less than 25 second response. timestamp: {time.time()}"
            
            messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": query})
            
            logger.info(f"Sending request to Grok: {query[:100]}...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                # Add some randomness to prevent repeated responses
                seed=int(time.time()) % 1000000  # Different seed each time
            )
            
            ai_response = response.choices[0].message.content
            
            # Clean up the response - remove escape characters and extra quotes
            if ai_response:
                # Remove leading/trailing quotes if present
                ai_response = ai_response.strip()
                if ai_response.startswith('"') and ai_response.endswith('"'):
                    ai_response = ai_response[1:-1]
                
                # Unescape common escape sequences
                ai_response = ai_response.replace('\\"', '"')
                ai_response = ai_response.replace('\\n', '\n')
                ai_response = ai_response.replace('\\t', '\t')
                ai_response = ai_response.replace('\\\\', '\\')
            
            logger.info(f"Received response from Grok: {len(ai_response)} characters")
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error getting Grok response: {str(e)}")
            raise

    def get_christmas_response(self, query: str) -> str:
        """Get a Christmas-themed snarky response from Grok"""
        system_prompt = f"""Be a smartass comedian. Be witty, irreverent. Make it different every time! It's christmas time, so make it about the Holiday. Not everything has to be nice! Not Skeleton jokes! Current time: {time.time()}"""
        
        return self.get_response(query, system_prompt)

    def get_snarky_response(self, query: str) -> str:
        """Get a general snarky response"""
        system_prompt = f"Be a smartass unhinged comedian (Like Norm McDonald), always tell a fresh, snarky joke. Mix it up and be unpredictable!No Skeleton jokes! Timestamp: {time.time()}"
        return self.get_response(query, system_prompt)
