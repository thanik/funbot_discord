class PromptBot:
    def getMessage(self, message, channel):
        message_content = message.content.strip()
        if 'ฮินาโนะ' in message_content:
            await self.safe_send_message(channel, 'เรียกหนูทำไมหรอ', also_delete=message)
        elif 'อีอ้วน' in message_content:
            await self.safe_send_message(channel, 'อย่าว่าพี่หนูนะ', also_delete=message)