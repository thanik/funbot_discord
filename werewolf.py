import logging
import random
from enums import BotMode
from enums import WerewolfGamePhase, WerewolfRole
import operator

PREPARING_TIME = 20
DAY_TIME = 300

MIN_PLAYERS = 4
log = logging.getLogger(__name__)


class Werewolf:
    kill_player_index: int
    look_player_index: int
    protect_player_index: int
    werewolf_index: int
    night_count: int

    def __init__(self):
        self.players = []
        self.roles = {}
        self.phase = WerewolfGamePhase.START
        self.werewolves = []
        self.werewolf_index = 0
        self.protect_player_index = -1
        self.kill_player_index = -1
        self.look_player_index = -1
        self.is_seer_died = False
        self.is_doctor_died = False
        self.playerlist = None
        self.kill_votes = {}
        self.kill_votes_count = {}
        self.alive_players = []
        self.night_count = 1

        self.day_message = None
        self.vote_kill_list_message = None

    async def trigger_timeout(self, client):
        log.info('Werewolf: Timeout')
        if self.phase == WerewolfGamePhase.START:
            log.info('Werewolf: Transition START to PREPARING')
            if len(self.players) < MIN_PLAYERS:
                await self.reset_game()
                await client.reset_vote()
                await client.safe_send_message(client.event_channel,
                                               'คนเล่นไม่พอค่ะ ต้อง ' + str(MIN_PLAYERS) + ' คนขึ้นไปนะคะ',
                                               expire_in=10)
                if self.playerlist is not None:
                    await client.safe_delete_message(self.playerlist)
                client.mode = BotMode.NONE
                await client.change_presence(activity=None)
            else:
                await client.safe_delete_message(self.playerlist)
                log.info('Change phase to PREPARING')
                self.phase = WerewolfGamePhase.PREPARING
                client.time = PREPARING_TIME
                # setup game
                random.shuffle(self.players)
                if len(self.players) > 6:
                    self.werewolves.append(self.players[0])
                    self.roles[self.players[0]] = WerewolfRole.WEREWOLF
                    self.werewolves.append(self.players[1])
                    self.roles[self.players[1]] = WerewolfRole.WEREWOLF
                    self.roles[self.players[2]] = WerewolfRole.SEER
                    self.roles[self.players[3]] = WerewolfRole.DOCTOR
                else:
                    self.werewolves.append(self.players[0])
                    self.roles[self.players[0]] = WerewolfRole.WEREWOLF
                    self.roles[self.players[1]] = WerewolfRole.SEER
                    self.roles[self.players[2]] = WerewolfRole.DOCTOR
                for player in self.players:
                    if player not in self.roles:
                        self.roles[player] = WerewolfRole.VILLAGER
                    self.alive_players.append(player)
                random.shuffle(self.players)
                random.shuffle(self.alive_players)

                # tell the roles
                for player in self.roles:
                    if player.dm_channel is None:
                        await player.create_dm()

                    all_player_msg = 'ในตอนกลางวัน คุณจะต้องร่วมกันโหวตเพื่อฆ่าผู้เล่นหนึ่งคนที่น่าสงสัย หากคุณเป็นชาวบ้าน จงหาตัวหมาป่าละฆ่าให้ได้ หากคุณเป็นหมาป่า จงระวังตัวไว้ให้ดี'
                    werewolf_list = 'มิตรสหายหมาป่าของคุณ:\n'
                    for werewolf in self.roles:
                        if self.roles[player] == WerewolfRole.WEREWOLF:
                            werewolf_list += werewolf.display_name + ' (' + werewolf.name + ')\n'
                    if self.roles[player] == WerewolfRole.WEREWOLF:
                        await client.safe_send_message(player.dm_channel,
                                                       '*หมาป่า*\nคุณคือหมาป่า หน้าที่ของคุณคือ คุณจะต้องฆ่าคนในหมู่บ้านในแต่ละคืน หากจำนวนชาวบ้านเท่ากับจำนวนหมาป่าในเกม หรือชาวบ้านตายหมด หมาป่าจะเป็นฝ่ายชนะ\n' + all_player_msg + '\n' + werewolf_list,
                                                       expire_in=0)
                    elif self.roles[player] == WerewolfRole.DOCTOR:
                        await client.safe_send_message(player.dm_channel, '*หมอ*\nคุณคือหมา เอ้ย หมอ คุณก็เป็นชาวบ้านคนหนึ่งที่สามารถป้องกันการฆ่าของหมาป่าในแต่ละคืนได้ โดยจะสามารถเลือกป้องกันตนเองหรือคนอื่นก็ได้\n' + all_player_msg, expire_in=0)

                    elif self.roles[player] == WerewolfRole.SEER:
                        await client.safe_send_message(player.dm_channel, '*เซียร์*\nคุณคือเซียร์ ผู้หยั่งรู้ ในแต่ละคืนเซียร์จะสามารถมองดูว่าคนๆ นั้นจริงๆ เป็นหมาป่าหรือไม่ โดยสามารถดูได้เพียงคืนละหนึ่งคนเท่านั้น\n' + all_player_msg, expire_in=0)

                    elif self.roles[player] == WerewolfRole.VILLAGER:
                        await client.safe_send_message(player.dm_channel, '*ชาวบ้าน*\nคุณคือชาวบ้านตาดำๆ ไม่มีพลังวิเศษใดๆ เลย เอาตัวรอดให้ได้ละกัน\n' + all_player_msg, expire_in=0)

                await client.safe_send_message(client.event_channel,
                                               'ทุกคนได้รับบทของตัวเองเรียบร้อยแล้ว คุณมีเวลาในการอ่านบทและทำความเข้าใจใน ' + str(
                                                   PREPARING_TIME) + ' วินาทีต่อจากนี้',
                                               expire_in=PREPARING_TIME)
        elif self.phase == WerewolfGamePhase.PREPARING:
            log.info('Werewolf: Transition PREPARING to NIGHT')
            await self.transition_to_night(client=client)
        elif self.phase == WerewolfGamePhase.DAY:
            log.info('Werewolf: Transition DAY to NIGHT')
            # vote killing process
            if len(self.kill_votes) == 0:
                await client.safe_send_message(client.event_channel, 'ไม่มีใครโหวตให้ฆ่าใคร พระอาทิตย์กำลังจะตกดิน...', expire_in=10)
            else:
                # find max vote
                killing_player = max(self.kill_votes_count.items(), key=operator.itemgetter(1))[0]
                # if wolf were kill
                if self.werewolves[self.werewolf_index] == killing_player:
                    self.werewolves.remove(killing_player)
                    if self.werewolf_index >= len(self.werewolves) - 1:
                        self.werewolf_index = 0
                self.alive_players.remove(killing_player)
                await client.safe_send_message(client.event_channel, 'สรุปผลโหวต: ' + killing_player.mention + ' จะถูกรุมประชาทัณฑ์จนตาย ลาก่อยค่ะ', expire_in=10)
            # check winning condition before transition
            if not await self.check_win_condition(client=client):
                await self.transition_to_night(client=client)

    async def transition_to_night(self, client):
        if self.day_message is not None:
            await client.safe_delete_message(self.day_message)
        # check winning condition before NIGHT cycle
        if not await self.check_win_condition(client=client):
            self.night_count += 1
            self.phase = WerewolfGamePhase.NIGHT
            self.protect_player_index = -1
            self.kill_player_index = -1
            self.look_player_index = -1
            await client.safe_send_message(client.event_channel, 'คืนที่ ' + str(self.night_count) + ' ในยามค่ำคืนนี้ เหล่าหมาป่าออกหากินเสียแล้ว... อาจจะมีชาวบ้านถูกจับฆ่าโดยไม่รู้ตัวก็ได้นะ.. หมาป่า คุณหมอ และเซียร์ ทำหน้าที่ของตัวเองด้วยค่ะ', expire_in=0)

            for player in self.alive_players:
                if self.roles[player] == WerewolfRole.DOCTOR:
                    await client.safe_send_message(
                        'โปรดเลือกคนที่คุณต้องการจะปกป้องจากการฆ่าของหมาป่า โดยพิมพ์ กัน ตามด้วยเลขประจำตัวของชาวบ้านที่ต้องการปกป้อง\n' + await self.print_player_choices(
                            self.alive_players))
                elif self.roles[player] == WerewolfRole.SEER:
                    await client.safe_send_message(
                        'โปรดเลือกคนที่คุณต้องการดูว่าเป็นหมาป่าหรือไม่ โดยพิมพ์ ดู ตามด้วยเลขประจำตัวของชาวบ้านที่ต้องการดู\n' + await self.print_player_choices(
                            self.alive_players))
                elif self.roles[player] == WerewolfRole.WEREWOLF:
                    if self.werewolves[self.werewolf_index] == player:
                        await client.safe_send_message(
                            'ตานี้เป็นตาของคุณในการเลือกจะฆ่าชาวบ้าน โปรดเลือกโดยพิมพ์ ฆ่า ตามด้วยเลขประจำตัวของชาวบ้านที่ต้องการฆ่า\n' + await self.print_player_choices(
                                self.alive_players))
                    else:
                        await client.safe_send_message(
                            'ตานี้ คุณยังไม่ใช่ตาของคุณในการเลือกจะฆ่าชาวบ้าน แต่คุณสามารถปรึกษาส่วนตัวกับหมาป่าอีกตัวได้')

    async def transition_to_day(self, client):
        self.phase = WerewolfGamePhase.DAY
        client.time = DAY_TIME
        if self.werewolf_index < len(self.werewolves) - 1:
            self.werewolf_index += 1
        else:
            self.werewolf_index = 0
        await client.safe_send_message(client.event_channel, 'พระอาทิตย์ขึ้นแล้ว ช่างเป็นเช้าอันสดใสเสียจริง')
        if self.kill_player_index == self.protect_player_index:
            await client.safe_send_message(client.event_channel, 'เมื่อคืนไม่มีคนตาย น่าอัศจรรย์ใจยิ่งนัก', expire_in=0)
        else:
            killed_player = self.alive_players[self.kill_player_index]
            await client.safe_send_message(client.event_channel, 'เมื่อคืนมีคนตาย คนๆ นั้นก็คือ ' + killed_player.mention + ' ขอแสดงความเสียใจด้วย', expire_in=0)
            # if wolf were kill
            if self.werewolves[self.werewolf_index] == killed_player:
                self.werewolves.remove(killed_player)
                if self.werewolf_index >= len(self.werewolves) - 1:
                    self.werewolf_index = 0
            self.alive_players.remove(killed_player)
        # reset vote
        self.kill_votes = {}
        self.kill_votes_count = {}
        for player in self.alive_players:
            self.kill_votes_count[player] = 0
        self.day_message = await client.safe_send_message(client.event_channel, 'พิมพ์ โหวต ตามด้วย @ ชื่อคนที่ต้องการจะโหวตให้ฆ่า หากโหวตไม่ฆ่าใครเลยให้พิมพ์ ไม่ฆ่า', expire_in=0)

    async def public_command(self, client, message):
        log.info('Werewolf: Public')
        message_content = message.content.strip()
        command, *args = message_content.split(
            ' ')  # Uh, doesn't this break prefixes with spaces in them (it doesn't, config parser already breaks them)
        command = command.lower().strip()
        args = ' '.join(args).lstrip(' ').split(' ')
        if command == 'เล่น' and self.phase == WerewolfGamePhase.START:
            if message.author in self.players:
                await client.safe_send_message(client.event_channel,
                                               message.author.mention + ' อยู่ในเกมแล้ว อีควาย',
                                               expire_in=10, also_delete=message)
            else:
                self.players.append(message.author)

            await self.print_playerlist(client)
            await client.safe_delete_message(message)
        elif command == 'ไม่เล่น' and self.phase == WerewolfGamePhase.START:
            if message.author in self.players:
                self.players.remove(message.author)
                await client.safe_send_message(client.event_channel, message.author.mention + ' ไม่เล่นก็เรื่องของมึงค่ะ',
                                           expire_in=10, also_delete=message)
            else:
                await client.safe_send_message(client.event_channel,
                                               message.author.mention + ' ไม่ได้เล่นอยู่แล้ว จะไม่เล่นอีกทำไม',
                                               expire_in=10, also_delete=message)
            await self.print_playerlist(client)
            await client.safe_delete_message(message)
        elif command == 'โหวต' and self.phase == WerewolfGamePhase.DAY:
            one_member = None
            if message.author in self.players:
                for player in self.players:
                    if player.mentioned_in(message):
                        one_member = player
                        break

                if one_member is None:
                    await client.safe_send_message(client.event_channel,
                                                   message.author.mention + ' คนนี้ไม่อยู่ในเกมค่ะ อีโง่',
                                                   expire_in=5, also_delete=message)
                else:
                    if message.author in self.kill_votes:
                        self.kill_votes_count[self.kill_votes[message.author]] -= 1
                    self.kill_votes[message.author] = one_member
                    self.kill_votes_count[one_member] += 1
                    if self.vote_kill_list_message is not None:
                        await client.safe_delete_message(self.vote_kill_list_message)
                    await client.safe_delete_message(message)
                    vote_message_string = message.author + ' ได้โหวตฆ่า ' + one_member.mention + '\n'
                    vote_message_string += await self.print_vote_kill_list()
                    self.vote_kill_list_message = await client.safe_send_message(client.event_channel, vote_message_string, expire_in=0)
            else:
                await client.safe_send_message(client.event_channel,
                                               message.author.mention + ' ไม่ได้อยู่ในเกม อย่าเสือกค่ะ',
                                               expire_in=10, also_delete=message)
        elif command == 'ไม่ฆ่า' and self.phase == WerewolfGamePhase.DAY:
            if message.author in self.players:
                if message.author in self.kill_votes:
                    self.kill_votes_count[self.kill_votes[message.author]] -= 1
                    self.kill_votes.pop(message.author)
                vote_message_string = message.author + ' ได้โหวตไม่ฆ่าใคร\n'
                vote_message_string += await self.print_vote_kill_list()
                self.vote_kill_list_message = await client.safe_send_message(client.event_channel, vote_message_string,
                                                                             expire_in=0)
            else:
                await client.safe_send_message(client.event_channel,
                                           message.author.mention + ' ไม่ได้อยู่ในเกม อย่าเสือกค่ะ',
                                           expire_in=10, also_delete=message)

    async def private_command(self, client, message):
        log.info('Werewolf: Private')
        message_content = message.content.strip()
        command, *args = message_content.split(
            ' ')  # Uh, doesn't this break prefixes with spaces in them (it doesn't, config parser already breaks them)
        command = command.lower().strip()
        args = ' '.join(args).lstrip(' ').split(' ')
        if message.author in self.alive_players:
            if command == 'ฆ่า' and self.phase == WerewolfGamePhase.NIGHT:
                if message.author in self.werewolves and len(args) == 2:
                    index = int(args[0])
                    if 0 < index < len(self.alive_players):
                        self.kill_player_index = index
                        name = self.alive_players[self.kill_player_index].display_name + ' (' + self.alive_players[self.kill_player_index].name + ')'
                        await client.safe_send_message(message.channel, 'คุณได้เลือก ' + name + ' เพื่อฆ่าทิ้งแล้ว', expire_in=0)
                        log.info(name + 'SELECTED FOR KILL')

                        if (self.is_doctor_died or self.protect_player_index != -1) and (self.is_seer_died or self.look_player_index != -1):
                            await self.transition_to_day(client=client)
                    else:
                        await client.safe_send_message(message.channel, 'เลขประจำตัวผู้เล่นไม่ถูกต้อง', expire_in=0)

            elif command == 'กัน' and self.phase == WerewolfGamePhase.NIGHT:
                if self.roles[message.author] == WerewolfRole.DOCTOR and len(args) == 2:
                    index = int(args[0])
                    if 0 < index < len(self.alive_players):
                        self.protect_player_index = index
                        name = self.alive_players[self.kill_player_index].display_name + ' (' + self.alive_players[
                            self.kill_player_index].name + ')'
                        await client.safe_send_message(message.channel, 'คุณได้เลือก ' + name + ' เพื่อป้องกันแล้ว',
                                                       expire_in=0)
                        log.info(name + 'SELECTED FOR PROTECT')

                        if self.kill_player_index != -1 and (self.is_seer_died or self.look_player_index != -1):
                            await self.transition_to_day(client=client)
                    else:
                        await client.safe_send_message(message.channel, 'เลขประจำตัวผู้เล่นไม่ถูกต้อง', expire_in=0)

            elif command == 'ดู' and self.phase == WerewolfGamePhase.NIGHT:
                if self.roles[message.author] == WerewolfRole.SEER and len(args) == 2:
                    index = int(args[0])
                    if 0 < index < len(self.alive_players):
                        self.look_player_index = index
                        name = self.alive_players[self.look_player_index].display_name + ' (' + self.alive_players[
                            self.look_player_index].name + ')'
                        if self.roles[self.alive_players[self.look_player_index]] == WerewolfRole.WEREWOLF:
                            await client.safe_send_message(message.channel, name + ' เป็นหมาป่า!',
                                                       expire_in=0)
                        else:
                            await client.safe_send_message(message.channel, name + ' ไม่ได้เป็นหมาป่า',
                                                           expire_in=0)

                        if self.kill_player_index != -1 and (self.is_doctor_died or self.protect_player_index != -1):
                            await self.transition_to_day(client=client)
                    else:
                        await client.safe_send_message(message.channel, 'เลขประจำตัวผู้เล่นไม่ถูกต้อง', expire_in=0)

    async def reset_game(self):
        self.players = []
        self.roles = {}
        self.phase = WerewolfGamePhase.START
        self.werewolves = []
        self.werewolf_index = 0
        self.protect_player_index = -1
        self.kill_player_index = -1
        self.look_player_index = -1
        self.is_seer_died = False
        self.is_doctor_died = False
        self.kill_votes = {}
        self.kill_votes_count = {}
        self.alive_players = []
        self.night_count = 1

    async def print_playerlist(self, client):
        output_message = 'เกม Werewolf พิมพ์ เล่น เพื่อร่วมเข้าเกม\nผู้เล่นในขณะนี้: \n'
        for player in self.players:
            output_message += player.mention + '\n'
        if self.playerlist is not None:
            await client.safe_delete_message(self.playerlist)
        self.playerlist = await client.safe_send_message(client.event_channel, output_message, expire_in=0)

    async def print_vote_kill_list(self):
        output_message = 'รายชื่อโหวตฆ่า:\n'
        for player in self.kill_votes:
            output_message += player.mention + ' ได้โหวตฆ่า ' + self.kill_votes[player].mention + '\n\n'
        if len(self.kill_votes_count) > 1:
            output_message += 'และคนที่โดนโหวตฆ่ามากที่สุดคือ: \n' + max(self.kill_votes_count.items(), key=operator.itemgetter(1))[0].mention
        return output_message

    async def print_player_choices(self, generating_list):
        output_message = 'รายชื่อ:\n'
        for i in range(0, len(generating_list)):
            output_message += '[' + str(i) + '] ' + generating_list[i].display_name + ' (' + generating_list[i].name + ')\n'
        return output_message

    async def check_win_condition(self, client):
        if len(self.werewolves) == 0:
            await self.game_over(client=client, is_werewolf_win=False)
            return True
        elif len(self.werewolves) == len(self.alive_players) - len(self.werewolves):
            await self.game_over(client=client, is_werewolf_win=True)
            return True
        else:
            return False

    async def game_over(self, client, is_werewolf_win):
        log.info('GAME OVER')
        self.phase = WerewolfGamePhase.END
        roles_names = {
            WerewolfRole.WEREWOLF: 'หมาป่า',
            WerewolfRole.SEER: 'เซียร์',
            WerewolfRole.DOCTOR: 'หมอ',
            WerewolfRole.VILLAGER: 'ชาวบ้าน'
        }
        roles_list = ''
        for player in self.roles:
            roles_list += player.mention + ' : ' + roles_names[self.roles[player]] + '\n'

        if is_werewolf_win:
            await client.safe_send_message(client.event_channel, 'ฝ่ายหมาป่าชนะ!\nเฉลยตำแหน่ง:\n' + roles_list, expire_in=0)
        else:
            await client.safe_send_message(client.event_channel, 'ฝ่ายชาวบ้านชนะ!\nเฉลยตำแหน่ง:\n' + roles_list, expire_in=0)

        client.mode = BotMode.NONE
        await client.change_presence(activity=None)
        await self.reset_game()
        await client.reset_vote()
