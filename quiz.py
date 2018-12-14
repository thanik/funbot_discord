import asyncio
import logging
import json
import random
from enums import BotMode
from enums import QuizGamePhase

log = logging.getLogger(__name__)

class Quiz:
    def __init__(self):
        self.players = []
        self.roles = {}
        self.phase = QuizGamePhase.START

    async def trigger_timeout(self, client):
        log.info('Quiz: Timeout')

    async def public_command(self, client, message):
        log.info('Quiz: Public')
        message_content = message.content.strip()
        command, *args = message_content.split(
            ' ')  # Uh, doesn't this break prefixes with spaces in them (it doesn't, config parser already breaks them)
        command = command.lower().strip()
        args = ' '.join(args).lstrip(' ').split(' ')

    async def private_command(self, client, message):
        log.info('Quiz: Private')
        message_content = message.content.strip()
        command, *args = message_content.split(
            ' ')  # Uh, doesn't this break prefixes with spaces in them (it doesn't, config parser already breaks them)
        command = command.lower().strip()
        args = ' '.join(args).lstrip(' ').split(' ')

    async def reset_game(self):
        self.players = []
