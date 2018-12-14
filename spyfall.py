import asyncio
import logging
import json
import random
from enums import BotMode
from enums import SpyfallGamePhase

GAME_TIME = 420
ENDING_PHASE_TIME = 31
MIN_PLAYERS = 3
log = logging.getLogger(__name__)

class Spyfall:
    def __init__(self):
        with open('configs/spyfall.json', 'r') as f:
            self.location_data = json.load(f)

        self.players = []
        self.roles = {}
        self.started = False
        self.phase = SpyfallGamePhase.START
        # self.host_id = 0
        self.location = None
        self.votes = {}
        self.playerlist = None
        self.voted_player = {}
        self.spies = []
        self.main_message = None

    async def print_playerlist(self, client):
        output_message = 'เกม Spyfall พิมพ์ เล่น เพื่อร่วมเข้าเกม\nผู้เล่นในขณะนี้: \n'
        for player in self.players:
            output_message += player.mention + '\n'
        if self.playerlist is not None:
            await client.safe_delete_message(self.playerlist)
        self.playerlist = await client.safe_send_message(client.event_channel, output_message, expire_in=0)

    async def public_command(self, client, message):
        log.info('Spyfall: Public')
        message_content = message.content.strip()
        command, *args = message_content.split(
            ' ')  # Uh, doesn't this break prefixes with spaces in them (it doesn't, config parser already breaks them)
        command = command.lower().strip()
        args = ' '.join(args).lstrip(' ').split(' ')
        if command == 'เล่น' and self.phase == SpyfallGamePhase.START:
            self.players.append(message.author)
            await self.print_playerlist(client)
            await client.safe_delete_message(message)
        elif command == 'ไม่เล่น' and self.phase == SpyfallGamePhase.START:
            self.players.remove(message.author)
            await client.safe_send_message(client.event_channel, message.author.mention + ' ไม่เล่นก็เรื่องของมึงค่ะ', expire_in=10, also_delete=message)
            await self.print_playerlist(client)
            await client.safe_delete_message(message)
        elif command == 'ทาย' and self.phase == SpyfallGamePhase.TALKING:
            if message.author in self.players:
                if message.author in self.voted_player:
                    self.votes[self.voted_player[message.author]] -= 1
                one_vote = None
                for player in self.players:
                    if player.mentioned_in(message):
                        self.votes[player] += 1
                        self.voted_player[message.author] = player
                        one_vote = player
                        break

                if one_vote is None:
                    await client.safe_send_message(client.event_channel,
                                                   message.author.mention + ' คนนี้ไม่อยู่ในเกมค่ะ อีโง่',
                                                   expire_in=5, also_delete=message)
                else:
                    await client.safe_send_message(client.event_channel,
                                                   message.author.mention + ' ทายว่า ' + one_vote.mention + ' เป็นสปาย',
                                                   expire_in=5, also_delete=message)
            else:
                await client.safe_send_message(client.event_channel,
                                               message.author.mention + ' ไม่ได้อยู่ในเกม อย่าเสือกค่ะ',
                                               expire_in=10, also_delete=message)

            # if len(self.players) == len(self.voted_player) and client.time < 1:
            #     end_message = self.result()
            #     log.info(end_message)
            #     await client.safe_send_message(client.event_channel, end_message, expire_in=20)
        elif command == 'เฉลย' and self.phase == SpyfallGamePhase.END:
            ending_message = await self.show_place()
            log.info(ending_message)
            await client.safe_send_message(client.event_channel, ending_message, expire_in=0, also_delete=message)
            await self.reset_game()
            await client.reset_vote()
            client.mode = BotMode.NONE
        elif command == 'ทาย' and self.phase == SpyfallGamePhase.ENDING:
            if message.author in self.spies:
                if args[0] == self.location['name']:
                    self.phase == SpyfallGamePhase.END
                    await client.safe_send_message(client.event_channel, message.author.mention +  ' ถูกต้องค่ะ ยินดีด้วยยย', expire_in=10, also_delete=message)
                    ending_message = await self.show_place()
                    log.info(ending_message)
                    await client.safe_send_message(client.event_channel, ending_message, expire_in=0,
                                                   also_delete=message)
                    await self.reset_game()
                    await client.reset_vote()
                else:
                    await client.safe_send_message(client.event_channel, message.author.mention +  ' เอ๊ะๆ พิมพ์ผิดหรือเปล่า ลองใหม่นะคะ', expire_in=10, also_delete=message)
            else:
                await client.safe_send_message(client.event_channel, message.author.mention + ' ไม่ใช่สปาย อย่าเสือกค่ะ', expire_in=10,
                                               also_delete=message)

    async def private_command(self, is_admin, client, message):
        message_content = message.content.strip()
        log.info('Spyfall: Private')
        if is_admin:
            log.info('is_admin: ' + str(is_admin) + ' message: ' + message_content)
            if message_content == 'stop':
                await self.reset_game()
                client.mode = BotMode.NONE
                client.reset_vote()
                await client.safe_send_message(message.channel, 'Current mode: ' + str(client.mode), expire_in=0)

    async def reset_game(self):
        self.players = []
        self.role = []
        self.phase = SpyfallGamePhase.START
        self.host_id = 0
        self.location = None
        self.votes = {}
        self.playerlist = None
        self.voted_player = {}
        self.spies = []

    async def ending(self,time):
        end_message = 'หมดเวลา! คะแนนโหวตมีดังนี้\n'
        for vote_for_player in self.votes:
            end_message += vote_for_player.mention + ' : ' + str(self.votes[vote_for_player]) + ' คะแนนโหวต\n'
        end_message += 'และสปายนั่นก็คือ... '
        for spy in self.spies:
            end_message += spy.mention + ' '
        end_message += '\nสปายมีเวลาทายสถานที่ ' + str(time) + ' วินาทีก่อนที่เกมจะจบ พิมพ์ ทาย ตามด้วยชื่อสถานที่เพื่อทายสถานที่'
        return end_message

    async def show_place(self):
        end_message = 'เฉลย: ทุกคนอยู่ที่ ' + self.location['name'] + '\n'
        for player in self.players:
            end_message += player.mention + ' : ' + self.roles[player] + '\n'
        end_message += 'จบเกมค่ะ'
        return end_message

    async def trigger_timeout(self, client):
        log.info('Spyfall: Timeout')
        if self.phase == SpyfallGamePhase.TALKING:
            self.phase = SpyfallGamePhase.ENDING
            client.time = ENDING_PHASE_TIME
            await client.safe_delete_message(self.main_message)
            ending_message = await self.ending(client.time)
            await client.safe_send_message(client.event_channel, ending_message, expire_in=0)
        elif self.phase == SpyfallGamePhase.START:
            if len(self.players) < MIN_PLAYERS:
                if self.playerlist is not None:
                    await client.safe_delete_message(self.playerlist)
                client.mode = BotMode.NONE
                await self.reset_game()
                await client.reset_vote()
                await client.safe_send_message(client.event_channel, 'คนเล่นไม่พอค่ะ ต้อง ' + str(MIN_PLAYERS) + ' คนขึ้นไปนะคะ', expire_in=10)
                await client.safe_delete_message(self.playerlist)
            else:
                await client.safe_delete_message(self.playerlist)
                self.phase = SpyfallGamePhase.TALKING
                client.time = GAME_TIME
                self.voted_player = {}
                # setup game
                self.location = random.choice(self.location_data['locations'])
                log.info('Location: ' + str(self.location))
                # if len(self.players) > 10:
                # 2 spies
                spy = random.choice(self.players)
                self.spies.append(spy)
                self.roles[spy] = 'สปาย'
                for player in self.players:
                    if player not in self.roles:
                        self.roles[player] = random.choice(self.location['roles'])
                log.info(str(self.roles))

                for player in self.players:
                    self.votes[player] = 0
                    if player.dm_channel is None:
                        await player.create_dm()

                    if self.roles[player] == 'สปาย':
                        await client.safe_send_message(player.dm_channel, 'Spyfall: คุณคือสปาย', expire_in=0)
                    else:
                        await client.safe_send_message(player.dm_channel, 'Spyfall: คุณอยู่ที่: ' + self.location['name'] + '\nคุณคือ: ' + self.roles[player], expire_in=0)

                main_msg_string = 'เกมเริ่มได้! คุณมีเวลา ' + str(client.time) + ' วินาที ในการหาตัวสปาย ใช้คำสั่ง ทาย แล้ว @ ชื่อเพื่อโหวตสปาย\n'
                main_msg_string += 'ผู้เล่นในขณะนี้: \n'
                for player in self.players:
                    main_msg_string += player.mention + '\n'
                self.main_message = await client.safe_send_message(client.event_channel, main_msg_string, expire_in=0)

        elif self.phase == SpyfallGamePhase.ENDING:
            await client.safe_send_message(client.event_channel, 'หมดเวลา! พิมพ์ เฉลย เพื่อดูสถานที่ และตำแหน่งแต่ละคน', expire_in=10)
            self.phase = SpyfallGamePhase.END
