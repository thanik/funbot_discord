class PromptBot:
    async def getMessage(self, client, message, channel):
        message_content = message.content.strip()
        if 'ฮินาโนะ' in message_content:
            await client.safe_send_message(channel, 'เรียกหนูทำไมหรอ', also_delete=message)
        elif 'อีอ้วน' in message_content:
            await client.safe_send_message(channel, 'อย่าว่าพี่หนูนะ', also_delete=message)

