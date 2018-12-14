import asyncio
import logging
import json
import random
from enums import BotMode
from enums import WerewolfGamePhase

TALKING_TIME = 420
log = logging.getLogger(__name__)

class Werewolf:
    def __init__(self):
        self.players = []
        self.roles = {}
        self.phase = WerewolfGamePhase.START

    async def trigger_timeout(self, client):
        log.info('Werewolf: Timeout')

    async def public_command(self, client, message):
        log.info('Werewolf: Public')
        message_content = message.content.strip()
        command, *args = message_content.split(
            ' ')  # Uh, doesn't this break prefixes with spaces in them (it doesn't, config parser already breaks them)
        command = command.lower().strip()
        args = ' '.join(args).lstrip(' ').split(' ')

    async def private_command(self, client, message):
        log.info('Werewolf: Private')
        message_content = message.content.strip()
        command, *args = message_content.split(
            ' ')  # Uh, doesn't this break prefixes with spaces in them (it doesn't, config parser already breaks them)
        command = command.lower().strip()
        args = ' '.join(args).lstrip(' ').split(' ')

    async def reset_game(self):
        self.players = []
