import base64


class SubscriptionDecoder:
    @staticmethod
    def decode(encoded_content: str) -> str:
        if not encoded_content:
            return ""

        try:
            missing_padding = len(encoded_content) % 4
            if missing_padding:
                encoded_content += "=" * (4 - missing_padding)

            decoded_bytes = base64.b64decode(encoded_content)
            return decoded_bytes.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Invalid base64 content: {e}")
