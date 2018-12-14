import discord
import asyncio
import logging
import operator
import json

from spyfall import Spyfall
from avalon import Avalon
from quiz import Quiz
from werewolf import Werewolf
from enums import BotMode

DISCORD_MSG_CHAR_LIMIT = 2000
VOTE_TIME = 11
LOBBY_TIME = 60

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class FunBot(discord.Client):
    def __init__(self):

        with open('configs/main.json', 'r') as f:
            self.config = json.load(f)

        self.spyfall = Spyfall()
        self.avalon = Avalon()
        self.quiz = Quiz()
        self.werewolf = Werewolf()
        self.mode = BotMode.NONE
        self.time = -1
        self.votes = {
            BotMode.SPYFALL: 0,
            BotMode.AVALON: 0,
            BotMode.WEREWOLF: 0,
            BotMode.QUIZ: 0
        }
        self.is_voting = False
        super().__init__()
        self.time_task = self.loop.create_task(self.countdown_task())

    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))
        self.event_channel = self.get_channel(self.config['CHANNEL_ID'])

    async def on_message(self, message):
        if message.author == self.user:
            log.debug("Ignoring command from myself ({})".format(message.content))
            return

        channel = message.channel
        if isinstance(channel, discord.channel.TextChannel) and channel.id == self.config['CHANNEL_ID']:
            await self.inside_event_room(message, channel)

        elif isinstance(channel, discord.channel.TextChannel):
            await self.outside_event_room(message, channel)

        elif isinstance(channel, discord.channel.DMChannel):
            await self.private_msg(message, channel)

    ## functions
    async def inside_event_room(self, message, channel):
        log.info('inside_event_room from {0.author} {0.channel.id}: {0.content}'.format(message))
        message_content = message.content.strip()
        command, *args = message_content.split(
            ' ')  # Uh, doesn't this break prefixes with spaces in them (it doesn't, config parser already breaks them)
        command = command.lower().strip()
        args = ' '.join(args).lstrip(' ').split(' ')

        if self.mode == BotMode.NONE:
            log.info('Mode: None')
            if command == 'เล่น' or command == 'p' and args[0] is not '':
                if not self.is_voting:
                    self.time = VOTE_TIME
                    self.is_voting = True
                    self.counting_down = True
                if args[0].lower() == 'spyfall':
                    self.votes[BotMode.SPYFALL] += 1
                elif args[0].lower() == 'avalon':
                    self.votes[BotMode.AVALON] += 1
                elif args[0].lower() == 'werewolf':
                    self.votes[BotMode.WEREWOLF] += 1
                elif args[0].lower() == 'quiz':
                    self.votes[BotMode.QUIZ] += 1
            vote_message = 'ผลโหวตเลือกเกม:\nSpyfall: ' + str(self.votes[BotMode.SPYFALL])
            vote_message += 'Avalon: ' + str(self.votes[BotMode.AVALON])
            vote_message += 'Werewolf: ' + str(self.votes[BotMode.WEREWOLF])
            vote_message += 'Quiz: ' + str(self.votes[BotMode.QUIZ])
            await self.safe_send_message(channel, vote_message, also_delete=message)
            log.info('Start counting down: ' + str(self.time))

        elif self.mode == BotMode.SPYFALL:
            log.info('Mode: Spyfall')
            await self.spyfall.public_command(client=self, message=message)
        elif self.mode == BotMode.AVALON:
            log.info('Mode: Avalon')
            await self.avalon.public_command(client=self, message=message)

    async def trigger_timeout(self):
        if self.mode == BotMode.NONE:
            self.is_voting = False
            self.time = LOBBY_TIME
            self.mode = max(self.votes.items(), key=operator.itemgetter(1))[0]
        log.info('Current mode: ' + str(self.mode))
        log.info('Time: ' + str(self.time))
        await self.safe_send_message(self.event_channel, 'พิมพ์ เล่น เพื่อเล่นเกม', expire_in=30)

    async def outside_event_room(self, message, channel):
        message_content = message.content.strip()
        if 'ฮินาโนะ' in message_content:
            await self.safe_send_message(channel, 'เรียกหนูทำไมหรอ', also_delete=message)
        elif 'อีอ้วน' in message_content:
            await self.safe_send_message(channel, 'อย่าว่าพี่หนูนะ', also_delete=message)
        elif 'โอ' in message_content:
            await self.safe_send_message(channel, 'ทรงพระแง้นๆ', also_delete=message, expire_in=1)

    async def private_msg(self, message, channel):
        print('Message from {0.author} {0.channel.id}: {0.content}'.format(message))
        if self.mode == BotMode.NONE:
            await self.admin_command_msg(message)
        elif self.mode == BotMode.SPYFALL:
            await self.spyfall.private_command(is_admin=message.author.id == self.config['ADMIN_ID'], client=self, message=message)
        elif self.mode == BotMode.AVALON:
            await self.avalon.private_command(is_admin=message.author.id == self.config['ADMIN_ID'], client=self, message=message)

            log.info('Mode: Avalon')
        # await self.safe_send_message(channel, 'สวัสดีค่ะ', expire_in=0)

    async def admin_command_msg(self, message):
        message_content = message.content.strip()
        command, *args = message_content.split(
            ' ')  # Uh, doesn't this break prefixes with spaces in them (it doesn't, config parser already breaks them)
        command = command.lower().strip()
        args = ' '.join(args).lstrip(' ').split(' ')
        log.info(args)
        if command == 'switch':
            if args[0] == 'spyfall':
                log.info('Switching to SPYFALL mode..')
                self.mode = BotMode.SPYFALL
            elif args[0] == '':
                log.info('Missing argument')
                await self.safe_send_message(message.channel, 'Missing argument', expire_in=0)
            await self.safe_send_message(message.channel, 'Current mode: ' + str(self.mode), expire_in=0)
        elif command == 'stop':
            self.mode = BotMode.NONE
            await self.safe_send_message(message.channel, 'Current mode: ' + str(self.mode), expire_in=0)

    ## utils
    async def reset_vote(self):
        self.votes = {
            BotMode.SPYFALL: 0,
            BotMode.AVALON: 0,
            BotMode.WEREWOLF: 0,
            BotMode.QUIZ: 0
        }
        client.time = -1

    async def countdown_task(self):
        await self.wait_until_ready()
        while not self.is_closed():
            log.info(str(self.time))
            channel = self.get_channel(self.config['CHANNEL_ID'])
            if self.time > 0:
                self.time -= 1
                if self.time % 60 == 0:
                    await self.safe_send_message(channel, 'เหลือเวลาอีก ' + str(self.time) + ' วินาที', expire_in=5)
                elif self.time % 30 == 0:
                    await self.safe_send_message(channel, 'เหลือเวลาอีก ' + str(self.time) + ' วินาที', expire_in=5)
                # elif self.time == 10:
                #     await self.safe_send_message(channel, 'เหลือเวลาอีก 10 วินาที', expire_in=5)
                elif self.time < 11:
                    await self.safe_send_message(channel, 'เหลือเวลาอีก ' + str(self.time) + ' วินาที', expire_in=1)
            elif self.time == 0:
                self.time = -1
                if self.mode == BotMode.NONE:
                    await self.trigger_timeout()
                elif self.mode == BotMode.SPYFALL:
                    await self.spyfall.trigger_timeout(client=self)
                elif self.mode == BotMode.AVALON:
                    await self.avalon.trigger_timeout(client=self)
            await asyncio.sleep(1)

    async def safe_send_message(self, dest, content, **kwargs):
        tts = kwargs.pop('tts', False)
        quiet = kwargs.pop('quiet', False)
        expire_in = kwargs.pop('expire_in', 10)
        allow_none = kwargs.pop('allow_none', True)
        also_delete = kwargs.pop('also_delete', None)

        msg = None
        lfunc = log.debug if quiet else log.warning

        try:
            if content is not None or allow_none:
                if isinstance(content, discord.Embed):
                    msg = await dest.send(embed=content)
                else:
                    msg = await dest.send(content, tts=tts)

        except discord.Forbidden:
            lfunc("Cannot send message to \"%s\", no permission", dest.name)

        except discord.NotFound:
            lfunc("Cannot send message to \"%s\", invalid channel?", dest.name)

        except discord.HTTPException:
            if len(content) > DISCORD_MSG_CHAR_LIMIT:
                lfunc("Message is over the message size limit (%s)", DISCORD_MSG_CHAR_LIMIT)
            else:
                lfunc("Failed to send message")
                log.noise("Got HTTPException trying to send message to %s: %s", dest, content)

        finally:
            if msg and expire_in:
                asyncio.ensure_future(self._wait_delete_msg(msg, expire_in))

            if also_delete and isinstance(also_delete, discord.Message):
                asyncio.ensure_future(self._wait_delete_msg(also_delete, expire_in))

        return msg

    async def _wait_delete_msg(self, message, after):
        await asyncio.sleep(after)
        await self.safe_delete_message(message, quiet=True)

    async def safe_delete_message(self, message, *, quiet=False):
        lfunc = log.debug if quiet else log.warning

        try:
            return await message.delete()

        except discord.Forbidden:
            lfunc("Cannot delete message \"{}\", no permission".format(message.clean_content))

        except discord.NotFound:
            lfunc("Cannot delete message \"{}\", message not found".format(message.clean_content))


client = FunBot()
client.run(self.config['TOKEN'])