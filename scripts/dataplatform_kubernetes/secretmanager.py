from google.cloud.secretmanager import SecretManagerServiceClient
from tenacity import retry, stop_after_attempt, wait_exponential


class SecretManagerClient:
    def __init__(self) -> None:
        super(SecretManagerClient, self).__init__()
        self._client = SecretManagerServiceClient()

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(), reraise=True)
    def get_secret(self, secret_name: str) -> str:
        resp = self._client.access_secret_version(name=secret_name)
        decoded: str = resp.payload.data.decode("UTF-8")
        return decoded
