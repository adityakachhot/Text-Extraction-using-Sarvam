import os
import time
import asyncio
from typing import Optional, Any
from sarvamai import SarvamAI, AsyncSarvamAI
from app.utils.logging_config import logger

class SarvamClient:
    """Wrapper for the Sarvam AI SDK clients with built-in retries and ZIP output parsing."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        llm_model: str = "sarvam-30b",
        temperature: float = 0.0,
        max_tokens: int = 4096,
        max_retries: int = 3,
        backoff_factor: float = 2.0
    ):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY")
        if not self.api_key:
            logger.error("SARVAM_API_KEY is not configured in the environment.")
            raise ValueError("SARVAM_API_KEY must be provided.")
            
        self.llm_model = os.getenv("SARVAM_LLM_MODEL", llm_model)
        self.temperature = float(os.getenv("SARVAM_LLM_TEMPERATURE", str(temperature)))
        self.max_tokens = int(os.getenv("SARVAM_LLM_MAX_TOKENS", str(max_tokens)))
        
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        
        # Initialize official SDK clients
        self.sync_sdk = SarvamAI(api_subscription_key=self.api_key)
        self.async_sdk = AsyncSarvamAI(api_subscription_key=self.api_key)
        logger.info(f"SarvamClient initialized with LLM model: {self.llm_model}")

    def _parse_downloaded_bytes(self, file_bytes: bytes) -> str:
        """Helper to check if bytes are a ZIP and extract the markdown/html text."""
        import zipfile
        import io
        
        if zipfile.is_zipfile(io.BytesIO(file_bytes)):
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                    logger.info(f"Downloaded output is a ZIP file. Contents: {z.namelist()}")
                    # Match markdown files
                    md_files = [name for name in z.namelist() if name.endswith(".md")]
                    if md_files:
                        return z.read(md_files[0]).decode("utf-8", errors="ignore")
                    # Match html files
                    html_files = [name for name in z.namelist() if name.endswith(".html")]
                    if html_files:
                        return z.read(html_files[0]).decode("utf-8", errors="ignore")
                    # Fallback to the first file in zip
                    if z.namelist():
                        return z.read(z.namelist()[0]).decode("utf-8", errors="ignore")
            except Exception as e:
                logger.error(f"Failed to extract ZIP archive: {e}")
                
        return file_bytes.decode("utf-8", errors="ignore")

    def digitize_document_sync(self, file_path: str, language: str = "en-IN") -> str:
        """Synchronously digitizes a document (PDF/Image) via Sarvam Document Intelligence."""
        retries = 0
        delay = 1.0
        while retries <= self.max_retries:
            try:
                logger.info(f"Submitting digitize job (Sync) for {file_path} in language {language}...")
                
                # Create job
                job = self.sync_sdk.document_intelligence.create_job(
                    language=language,
                    output_format="md"
                )
                
                # Run convenience workflow: upload -> start -> wait -> download
                job.upload_file(file_path)
                job.start()
                job.wait_until_complete()
                
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_out:
                    temp_out_path = temp_out.name
                
                try:
                    job.download_output(temp_out_path)
                    with open(temp_out_path, "rb") as f:
                        file_bytes = f.read()
                    
                    markdown_content = self._parse_downloaded_bytes(file_bytes)
                    logger.info("Digitization completed successfully (Sync).")
                    return markdown_content
                finally:
                    if os.path.exists(temp_out_path):
                        os.remove(temp_out_path)
                        
            except Exception as e:
                err_str = str(e).lower()
                # Do not retry on content policy violations or corrupted PDFs
                if any(kw in err_str for kw in ["content_filter", "content policy", "corrupted pdf", "corrupt pdf", "invalid pdf"]):
                    logger.warning(f"Terminal OCR digitization error: {e}. Skipping retries.")
                    raise
                retries += 1
                if retries > self.max_retries:
                    logger.error(f"OCR digitization failed after {self.max_retries} retries: {e}")
                    raise
                # Use a longer wait for rate-limit / quota errors
                is_rate_limit = any(kw in err_str for kw in ["429", "rate_limit", "rate limit", "insufficient_quota", "no credits"])
                wait = 60.0 if is_rate_limit else delay
                logger.warning(f"OCR digitization error (rate_limit={is_rate_limit}): {e}. Retrying in {wait:.1f}s (Attempt {retries}/{self.max_retries})...")
                time.sleep(wait)
                if not is_rate_limit:
                    delay *= self.backoff_factor

    async def digitize_document_async(self, file_path: str, language: str = "en-IN") -> str:
        """Asynchronously digitizes a document (PDF/Image) via Sarvam Document Intelligence."""
        retries = 0
        delay = 1.0
        while retries <= self.max_retries:
            try:
                logger.info(f"Submitting digitize job (Async) for {file_path} in language {language}...")
                
                # Create job
                job = await self.async_sdk.document_intelligence.create_job(
                    language=language,
                    output_format="md"
                )
                
                # Run convenience workflow: upload -> start -> wait -> download
                await job.upload_file(file_path)
                await job.start()
                await job.wait_until_complete()
                
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_out:
                    temp_out_path = temp_out.name
                
                try:
                    await job.download_output(temp_out_path)
                    with open(temp_out_path, "rb") as f:
                        file_bytes = f.read()
                    
                    markdown_content = self._parse_downloaded_bytes(file_bytes)
                    logger.info("Digitization completed successfully (Async).")
                    return markdown_content
                finally:
                    if os.path.exists(temp_out_path):
                        os.remove(temp_out_path)
                        
            except Exception as e:
                err_str = str(e).lower()
                # Do not retry on content policy violations or corrupted PDFs
                if any(kw in err_str for kw in ["content_filter", "content policy", "corrupted pdf", "corrupt pdf", "invalid pdf"]):
                    logger.warning(f"Terminal OCR digitization error (Async): {e}. Skipping retries.")
                    raise
                retries += 1
                if retries > self.max_retries:
                    logger.error(f"OCR digitization failed after {self.max_retries} retries (Async): {e}")
                    raise
                is_rate_limit = any(kw in err_str for kw in ["429", "rate_limit", "rate limit", "insufficient_quota", "no credits"])
                wait = 60.0 if is_rate_limit else delay
                logger.warning(f"OCR digitization error (Async, rate_limit={is_rate_limit}): {e}. Retrying in {wait:.1f}s (Attempt {retries}/{self.max_retries})...")
                await asyncio.sleep(wait)
                if not is_rate_limit:
                    delay *= self.backoff_factor

    def get_chat_completion_sync(self, system_prompt: str, user_prompt: str, temperature: Optional[float] = None) -> str:
        """Synchronously calls Sarvam chat completions API to extract structured fields."""
        retries = 0
        delay = 1.0
        while retries <= self.max_retries:
            try:
                current_temp = temperature if temperature is not None else self.temperature
                if retries > 0:
                    current_temp = min(0.9, current_temp + retries * 0.3)
                logger.info(f"Requesting chat completion (Sync) using model {self.llm_model} at temp {current_temp}...")
                logger.debug(f"Request Payload (Sync): System Prompt: {repr(system_prompt)}, User Prompt: {repr(user_prompt)}")
                
                response = self.sync_sdk.chat.completions(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=current_temp,
                    max_tokens=self.max_tokens
                )
                
                # Detailed diagnostic logging for the response
                logger.info(f"Chat completion completed successfully (Sync).")
                logger.info(f"Response type (Sync): {type(response)}")
                logger.info(f"Response repr (Sync): {repr(response)}")
                logger.info(f"Response attributes (Sync): {dir(response)}")
                
                # Try to serialize or dump the response object
                try:
                    if hasattr(response, "model_dump"):
                        logger.info(f"Response model_dump (Sync): {response.model_dump()}")
                    elif hasattr(response, "dict"):
                        logger.info(f"Response dict (Sync): {response.dict()}")
                    elif hasattr(response, "json"):
                        logger.info(f"Response json (Sync): {response.json()}")
                    else:
                        logger.info(f"Response dict representation (Sync): {vars(response)}")
                except Exception as dump_err:
                    logger.warning(f"Could not dump response (Sync): {dump_err}")
                
                # Attempt standard choices extraction
                content = None
                try:
                    if hasattr(response, "choices") and response.choices:
                        logger.info(f"Choices structure (Sync): {response.choices}")
                        choice = response.choices[0]
                        logger.info(f"Choice[0] type (Sync): {type(choice)}")
                        logger.info(f"Choice[0] repr (Sync): {repr(choice)}")
                        if hasattr(choice, "finish_reason") and choice.finish_reason == "content_filter":
                            raise ValueError("Chat completion was blocked by safety content_filter")
                        if hasattr(choice, "message"):
                            message = choice.message
                            logger.info(f"Message type (Sync): {type(message)}")
                            logger.info(f"Message repr (Sync): {repr(message)}")
                            if hasattr(message, "content"):
                                content = message.content
                                logger.info(f"Extracted content via choices[0].message.content (Sync): {repr(content)}")
                except Exception as choices_err:
                    if "content_filter" in str(choices_err):
                        raise
                    logger.warning(f"Error accessing choices (Sync): {choices_err}")
                
                # Check for other common fields (answer, output, text, etc.)
                if content is None:
                    logger.info("Content extracted via standard path is None. Checking fallback fields...")
                    if hasattr(response, "output") and response.output:
                        logger.info(f"Fallback 'output' field found: {response.output}")
                        if isinstance(response.output, dict) and "text" in response.output:
                            content = response.output["text"]
                        elif hasattr(response.output, "text"):
                            content = response.output.text
                    elif hasattr(response, "answer"):
                        logger.info(f"Fallback 'answer' field found: {response.answer}")
                        content = response.answer
                    elif isinstance(response, dict):
                        # If response is a dict
                        if "choices" in response and response["choices"]:
                            content = response["choices"][0].get("message", {}).get("content")
                        elif "output" in response and isinstance(response["output"], dict):
                            content = response["output"].get("text")
                        elif "answer" in response:
                            content = response["answer"]
                
                logger.info(f"Final extracted text content (Sync): {repr(content)}")
                # Retry if LLM returned empty content
                if content is None:
                    retries += 1
                    if retries > self.max_retries:
                        logger.error(f"Chat completion returned None content after {self.max_retries} retries.")
                        return content
                    logger.warning(f"Chat completion returned None content. Retrying in {delay:.1f}s (Attempt {retries}/{self.max_retries})...")
                    time.sleep(delay)
                    delay *= self.backoff_factor
                    continue
                return content
            except Exception as e:
                err_str = str(e).lower()
                if "content_filter" in err_str or "content policy" in err_str:
                    logger.warning(f"Terminal chat completion safety filter block: {e}. Skipping retries.")
                    raise
                retries += 1
                if retries > self.max_retries:
                    logger.error(f"Chat completion failed after {self.max_retries} retries: {e}")
                    raise
                is_rate_limit = any(kw in err_str for kw in ["429", "rate_limit", "rate limit", "insufficient_quota", "no credits"])
                wait = 60.0 if is_rate_limit else delay
                logger.warning(f"Chat completion error (rate_limit={is_rate_limit}): {e}. Retrying in {wait:.1f}s (Attempt {retries}/{self.max_retries})...")
                time.sleep(wait)
                if not is_rate_limit:
                    delay *= self.backoff_factor

    async def get_chat_completion_async(self, system_prompt: str, user_prompt: str, temperature: Optional[float] = None) -> str:
        """Asynchronously calls Sarvam chat completions API to extract structured fields."""
        retries = 0
        delay = 1.0
        while retries <= self.max_retries:
            try:
                current_temp = temperature if temperature is not None else self.temperature
                if retries > 0:
                    current_temp = min(0.9, current_temp + retries * 0.3)
                logger.info(f"Requesting chat completion (Async) using model {self.llm_model} at temp {current_temp}...")
                logger.debug(f"Request Payload (Async): System Prompt: {repr(system_prompt)}, User Prompt: {repr(user_prompt)}")
                
                response = await self.async_sdk.chat.completions(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=current_temp,
                    max_tokens=self.max_tokens
                )
                
                # Detailed diagnostic logging for the response
                logger.info(f"Chat completion completed successfully (Async).")
                logger.info(f"Response type (Async): {type(response)}")
                logger.info(f"Response repr (Async): {repr(response)}")
                logger.info(f"Response attributes (Async): {dir(response)}")
                
                # Try to serialize or dump the response object
                try:
                    if hasattr(response, "model_dump"):
                        logger.info(f"Response model_dump (Async): {response.model_dump()}")
                    elif hasattr(response, "dict"):
                        logger.info(f"Response dict (Async): {response.dict()}")
                    elif hasattr(response, "json"):
                        logger.info(f"Response json (Async): {response.json()}")
                    else:
                        logger.info(f"Response dict representation (Async): {vars(response)}")
                except Exception as dump_err:
                    logger.warning(f"Could not dump response (Async): {dump_err}")
                
                # Attempt standard choices extraction
                content = None
                try:
                    if hasattr(response, "choices") and response.choices:
                        logger.info(f"Choices structure (Async): {response.choices}")
                        choice = response.choices[0]
                        logger.info(f"Choice[0] type (Async): {type(choice)}")
                        logger.info(f"Choice[0] repr (Async): {repr(choice)}")
                        if hasattr(choice, "finish_reason") and choice.finish_reason == "content_filter":
                            raise ValueError("Chat completion was blocked by safety content_filter")
                        if hasattr(choice, "message"):
                            message = choice.message
                            logger.info(f"Message type (Async): {type(message)}")
                            logger.info(f"Message repr (Async): {repr(message)}")
                            if hasattr(message, "content"):
                                content = message.content
                                logger.info(f"Extracted content via choices[0].message.content (Async): {repr(content)}")
                except Exception as choices_err:
                    if "content_filter" in str(choices_err):
                        raise
                    logger.warning(f"Error accessing choices (Async): {choices_err}")
                
                # Check for other common fields (answer, output, text, etc.)
                if content is None:
                    logger.info("Content extracted via standard path is None. Checking fallback fields...")
                    if hasattr(response, "output") and response.output:
                        logger.info(f"Fallback 'output' field found: {response.output}")
                        if isinstance(response.output, dict) and "text" in response.output:
                            content = response.output["text"]
                        elif hasattr(response.output, "text"):
                            content = response.output.text
                    elif hasattr(response, "answer"):
                        logger.info(f"Fallback 'answer' field found: {response.answer}")
                        content = response.answer
                    elif isinstance(response, dict):
                        # If response is a dict
                        if "choices" in response and response["choices"]:
                            content = response["choices"][0].get("message", {}).get("content")
                        elif "output" in response and isinstance(response["output"], dict):
                            content = response["output"].get("text")
                        elif "answer" in response:
                            content = response["answer"]
                
                logger.info(f"Final extracted text content (Async): {repr(content)}")
                # Retry if LLM returned empty content
                if content is None:
                    retries += 1
                    if retries > self.max_retries:
                        logger.error(f"Chat completion (Async) returned None content after {self.max_retries} retries.")
                        return content
                    logger.warning(f"Chat completion (Async) returned None content. Retrying in {delay:.1f}s (Attempt {retries}/{self.max_retries})...")
                    await asyncio.sleep(delay)
                    delay *= self.backoff_factor
                    continue
                return content
            except Exception as e:
                err_str = str(e).lower()
                if "content_filter" in err_str or "content policy" in err_str:
                    logger.warning(f"Terminal chat completion safety filter block (Async): {e}. Skipping retries.")
                    raise
                retries += 1
                if retries > self.max_retries:
                    logger.error(f"Chat completion failed after {self.max_retries} retries (Async): {e}")
                    raise
                is_rate_limit = any(kw in err_str for kw in ["429", "rate_limit", "rate limit", "insufficient_quota", "no credits"])
                wait = 60.0 if is_rate_limit else delay
                logger.warning(f"Chat completion error (Async, rate_limit={is_rate_limit}): {e}. Retrying in {wait:.1f}s (Attempt {retries}/{self.max_retries})...")
                await asyncio.sleep(wait)
                if not is_rate_limit:
                    delay *= self.backoff_factor
