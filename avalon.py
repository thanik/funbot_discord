import asyncio
import logging
import json
import random
from enums import BotMode
from enums import AvalonGamePhase, AvalonRoles, AvalonTeamVote, AvalonMissionVote

TEAM_BUILDING_TIME = 300
PREPARING_TIME = 20
MISSION_TIME = 30
ENDING_ROUND_TIME = 10

MIN_PLAYERS = 5
MAX_PLAYERS = 10
log = logging.getLogger(__name__)

class Avalon:
    def __init__(self):
        with open('configs/avalon.json', 'r') as f:
            self.config = json.load(f)
        self.players = []
        self.roles = {}
        self.round = 1

        self.votes_mission_team = {}
        self.votes_mission = {}
        self.mission_team_members = []

        self.evil_players = []
        self.approve_team_vote_count = 0
        self.reject_team_vote_count = 0
        self.mission_passed_vote_count = 0
        self.mission_failed_vote_count = 0

        self.main_message = None
        self.mission_message = None
        self.team_building_message = None
        self.team_building_memberlist_message = None
        self.team_voting_message = None
        self.playerlist = None
        self.ending_message = None

        self.phase = AvalonGamePhase.START
        self.failed_missions_count = 0
        self.success_missions_count = 0
        self.leader_player_index = 0
        self.vote_reject_steak = 0

    async def trigger_timeout(self, client):
        log.info('Avalon: Timeout')
        if self.phase == AvalonGamePhase.START:
            log.info('Avalon: Transition START to PREPARING')
            if len(self.players) < MIN_PLAYERS:
                client.mode = BotMode.NONE
                await client.change_presence(activity=None)
                await self.reset_game()
                await client.reset_vote()
                await client.safe_send_message(client.event_channel,
                                               'คนเล่นไม่พอค่ะ ต้อง ' + str(MIN_PLAYERS) + ' คนขึ้นไปนะคะ',
                                               expire_in=10)
                await client.safe_delete_message(self.playerlist)
            else:
                await client.safe_delete_message(self.playerlist)
                log.info('Change phase to PREPARING')
                self.phase = AvalonGamePhase.PREPARING
                client.time = PREPARING_TIME
                # setup game
                good_player_count = 0
                evil_player_count = 0
                evil_player_list = ''
                random.shuffle(self.players)
                for player in self.players:
                    if good_player_count < self.config['good_evil_players'][str(len(self.players))]['good']:
                        if good_player_count == 0:
                            self.roles[player] = AvalonRoles.MERLIN
                        else:
                            self.roles[player] = AvalonRoles.ARTHUR_MINION
                        good_player_count += 1
                    else:
                        if evil_player_count == 0:
                            self.roles[player] = AvalonRoles.ASSASSIN
                        else:
                            self.roles[player] = AvalonRoles.MORDRED_MINION
                        self.evil_players.append(player)
                        evil_player_count += 1
                        evil_player_list += player.display_name + ' (' + player.name + ')\n'

                    self.votes_mission_team[player] = AvalonTeamVote.NONE

                # tell the roles
                for player in self.roles:
                    if player.dm_channel is None:
                        await player.create_dm()

                    if self.roles[player] == AvalonRoles.MERLIN:
                        await client.safe_send_message(player.dm_channel, '*ฝั่งคนดี*\nคุณคือเมอร์ลิน คุณสามารถลืมตาเพื่อดูอนาคตได้ คุณจะล่วงรู้ว่าเหล่าสาวกของมอร์เดร็ดอันเลวร้ายมีใครบ้าง โปรดระวังนักฆ่าในหมู่สาวกของมอร์เดร็ดเพราะถ้าเขารู้ตัวคุณ ความพยายามทั้งหมดที่ทำมาอาจพังทลายได้ และ', expire_in=0)
                    elif self.roles[player] == AvalonRoles.ASSASSIN:
                        await client.safe_send_message(player.dm_channel,
                                                       '*ฝั่งคนร้าย*\nคุณคือนักฆ่า หากเหล่าคนดีทำภารกิจสำเร็จครบ 3 ภารกิจ คุณจะสามารถพลิกเกมให้ชนะได้โดยฆ่าเมอร์ลินให้ได้ และ', expire_in=0)
                    elif self.roles[player] == AvalonRoles.MORDRED_MINION:
                        await client.safe_send_message(player.dm_channel, '*ฝั่งคนร้าย*\nคุณคือเหล่าสาวกของมอร์เดร็ด สิ่งที่คุณจะต้องทำคือ อย่าให้เหล่าคนดีทำภารกิจสำเร็จจนครบ 3 ภารกิจให้ได้ และ', expire_in=0)
                    elif self.roles[player] == AvalonRoles.ARTHUR_MINION:
                        await client.safe_send_message(player.dm_channel, '*ฝั่งคนดี*\nคุณคือลูกสมุนแห่งอาเธอร์ สิ่งที่คุณจะต้องทำคือ พยายามหาเหล่าคนร้ายในหมู่ของพวกคุณ และทำให้ภารกิจสำเร็จ 3 ภารกิจให้ได้', expire_in=0)

                    if self.roles[player] == AvalonRoles.ASSASSIN or self.roles[player] == AvalonRoles.MORDRED_MINION or self.roles[player] == AvalonRoles.MERLIN:
                        await client.safe_send_message(player.dm_channel, '\nนี่คือเหล่าสาวกของมอร์เดร็ดทั้งหมด รู้จักกับพวกเขาไว้ซะ\n' + evil_player_list, expire_in=0)

                await client.safe_send_message(client.event_channel,
                                                   'ทุกคนได้รับบทของตัวเองเรียบร้อยแล้ว คุณมีเวลาในการอ่านบทและทำความเข้าใจใน ' + str(PREPARING_TIME) + ' วินาทีต่อจากนี้',
                                                   expire_in=PREPARING_TIME)

        elif self.phase == AvalonGamePhase.PREPARING:
            log.info('Avalon: Transition PREPARING to TEAM_BUILDING')
            client.time = TEAM_BUILDING_TIME
            self.phase = AvalonGamePhase.TEAM_BUILDING
            leader = self.players[self.leader_player_index]
            team_building_msg_string = 'ภารกิจที่ ' + str(self.round) + '\nหัวหน้าในการทำภารกิจครั้งนี้คือ ' + leader.mention + '\nพิมพ์ เลือก ตามด้วย @ ชื่อคนทีละคนเพื่อคัดเลือกคนเข้าทีมไปทำภารกิจ\nพิมพ์ ไม่เลือก ตามด้วย @ ชื่อคนทีละคน เพื่อนำคนออกจากทีมทำภารกิจ\nพิมพ์ ยืนยัน เพื่อยืนยันสมาชิกในทีมทำภารกิจ\nภารกิจนี้ต้องใช้ ' + str(self.config['mission_players'][str(len(self.players))][str(self.round)]) + ' คน\nผู้เล่นในขณะนี้: \n'
            for player in self.players:
                team_building_msg_string += player.mention + '\n'
            self.team_building_message = await client.safe_send_message(client.event_channel, team_building_msg_string, expire_in=0)

        elif self.phase == AvalonGamePhase.TEAM_BUILDING:
            log.info('Avalon: Transition TEAM_BUILDING to TEAM_VOTING')
            if len(self.mission_team_members) < self.config['mission_players'][str(len(self.players))][str(self.round)]:
                await client.safe_send_message(client.event_channel,'หมดเวลาในการเลือกทีมแล้ว โปรดเลือกสมาชิกให้ครบแล้วจะเริ่มทำการโหวตผ่านไม่ผ่านทีมทันที', expire_in=15)
            else:
                await client.safe_send_message(client.event_channel,
                                               'ช่วงอภิปรายไม่ไว้วางใจ คุณไว้ใจทีมทำภารกิจนี้หรือไม่ พิมพ์ ผ่าน เพื่อให้ทีมนี้ไปทำภารกิจได้ พิมพ์ ไม่ผ่าน เพื่อไม่ให้ทีมนี้ไปทำภารกิจ',
                                               expire_in=45)
                self.phase = AvalonGamePhase.TEAM_VOTING
                for player in self.players:
                    self.votes_mission_team[player] = AvalonTeamVote.NONE
                self.approve_team_vote_count = 0
                self.reject_team_vote_count = 0
                log.info('Change phase to TEAM_VOTING')

        elif self.phase == AvalonGamePhase.MISSION:
            log.info('Avalon: Transition MISSION to ENDING_ROUND')
            self.phase = AvalonGamePhase.ENDING_ROUND
            mission_result_msg = 'โหวตภารกิจสำเร็จ: ' + str(self.mission_passed_vote_count) + '\nโหวตภารกิจล้มเหลว: ' + str(self.mission_failed_vote_count)
            if self.mission_failed_vote_count > 0:
                # mission failed
                log.info('Mission failed')
                self.failed_missions_count += 1
                mission_result_msg += '\nภารกิจสำเร็จไปแล้ว: ' + str(self.success_missions_count) + '\nภารกิจล้มเหลวไปแล้ว: ' + str(self.failed_missions_count)
                await client.safe_send_message(client.event_channel, 'ภารกิจล้มเหลว เนื่องจากมีสมาชิกในทีมอย่างน้อยหนึ่งคนทำภารกิจไม่สำเร็จ\n' + mission_result_msg, expire_in=45)
            elif self.round == 4 and len(self.players) > 6 and self.mission_failed_vote_count > 1:
                # mission failed
                log.info('Mission failed')
                self.failed_missions_count += 1
                mission_result_msg += '\nภารกิจสำเร็จไปแล้ว: ' + str(
                    self.success_missions_count) + '\nภารกิจล้มเหลวไปแล้ว: ' + str(self.failed_missions_count)
                await client.safe_send_message(client.event_channel,
                                               'ภารกิจล้มเหลว เนื่องจากเป็นรอบที่ 4 มีผู้เล่นอย่างน้อย 7 คน และมีสมาชิกในทีมทำภารกิจไม่สำเร็จ 2 คนขึ้นไป\n' + mission_result_msg,
                                               expire_in=45)
            else:
                # mission passed
                log.info('Mission passed')
                self.success_missions_count += 1
                mission_result_msg += '\nภารกิจสำเร็จไปแล้ว: ' + str(
                    self.success_missions_count) + '\nภารกิจล้มเหลวไปแล้ว: ' + str(self.failed_missions_count)
                await client.safe_send_message(client.event_channel,
                                   'ภารกิจสำเร็จ\n' + mission_result_msg, expire_in=45)

            self.round += 1
            if self.failed_missions_count == 3:
                await self.game_over(client, is_good_win=False)
            elif self.success_missions_count == 3:
                # transition to ENDING for assassination
                self.phase = AvalonGamePhase.ENDING
                log.info('Change phase to ENDING')
                self.ending_message = await client.safe_send_message(client.event_channel, 'สุดยอดมาก ฝ่ายอาเธอร์ทำภารกิจสำเร็จสามครั้ง \nนี่เป็นโอกาสสุดท้ายของฝ่ายมอร์เดร็ด นักฆ่าจงฆ่าเมอร์ลินให้ถูกคน แล้วฝ่ายมอร์เดร็ดจะชนะในทันที พิมพ์ ฆ่า แล้วตามด้วย @ ชื่อคน', expire_in=0)
            else:
                # transition to new round
                self.leader_player_index += 1
                self.phase = AvalonGamePhase.TEAM_BUILDING
                log.info('Change phase to TEAM_BUILDING')
                client.time = TEAM_BUILDING_TIME
                leader = self.players[self.leader_player_index]
                self.mission_team_members = []
                self.approve_team_vote_count = 0
                self.reject_team_vote_count = 0
                team_building_msg_string = 'ภารกิจที่ ' + str(
                    self.round) + '\nหัวหน้าในการทำภารกิจครั้งนี้คือ ' + leader.mention + '\nพิมพ์ เลือก ตามด้วย @ ชื่อคนทีละคนเพื่อคัดเลือกคนเข้าทีมไปทำภารกิจ\nพิมพ์ ไม่เลือก ตามด้วย @ ชื่อคนทีละคน เพื่อนำคนออกจากทีมทำภารกิจ\nพิมพ์ ยืนยัน เพื่อยืนยันสมาชิกในทีมทำภารกิจ\nภารกิจนี้ต้องใช้ ' + str(self.config['mission_players'][str(len(self.players))][str(self.round)]) + ' คน\nผู้เล่นในขณะนี้: \n'
                for player in self.players:
                    team_building_msg_string += player.mention + '\n'
                self.team_building_message = await client.safe_send_message(client.event_channel,
                                                                            team_building_msg_string,
                                                                            expire_in=0)

    async def public_command(self, client, message):
        log.info('Avalon: Public')
        message_content = message.content.strip()
        command, *args = message_content.split(
            ' ')  # Uh, doesn't this break prefixes with spaces in them (it doesn't, config parser already breaks them)
        command = command.lower().strip()
        args = ' '.join(args).lstrip(' ').split(' ')
        if command == 'เล่น' and self.phase == AvalonGamePhase.START:
            if len(self.players) == MAX_PLAYERS:
                await client.safe_send_message(client.event_channel,
                                               message.author.mention + ' เกมนี้คนเต็มแล้วค่ะ ขอโทษด้วยนะคะ',
                                               expire_in=10, also_delete=message)
            else:
                if message.author in self.players:
                    await client.safe_send_message(client.event_channel,
                                                   message.author.mention + ' อยู่ในเกมแล้ว อีควาย',
                                                   expire_in=10, also_delete=message)
                else:
                    self.players.append(message.author)

                await self.print_playerlist(client)
                await client.safe_delete_message(message)
        elif command == 'ไม่เล่น' and self.phase == AvalonGamePhase.START:
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
        elif command == 'เลือก' and self.phase == AvalonGamePhase.TEAM_BUILDING:
            one_member = None
            if message.author is self.players[self.leader_player_index]:
                for player in self.players:
                    if player.mentioned_in(message):
                        one_member = player
                        break

                if one_member is None:
                    await client.safe_send_message(client.event_channel,
                                                   message.author.mention + ' คนนี้ไม่อยู่ในเกมค่ะ อีโง่',
                                                   expire_in=5, also_delete=message)
                else:
                    if len(self.mission_team_members) < self.config['mission_players'][str(len(self.players))][str(self.round)]:
                        self.mission_team_members.append(player)
                    else:
                        await client.safe_send_message(client.event_channel,
                                                       message.author.mention + ' คนในทีมครบแล้วค่ะ เลือกเพิ่มไม่ได้แล้ว',
                                                       expire_in=5, also_delete=message)

                await self.print_mission_memberlist(client)
                await client.safe_delete_message(message)

                if client.time < 1 and len(self.mission_team_members) == self.config['mission_players'][str(len(self.players))][str(self.round)]:
                    log.info('Change phase to TEAM_VOTING')
                    self.phase = AvalonGamePhase.TEAM_VOTING
                    for player in self.players:
                        self.votes_mission_team[player] = AvalonTeamVote.NONE
                    self.approve_team_vote_count = 0
                    self.reject_team_vote_count = 0
                    client.time = -1
                    await client.safe_send_message(client.event_channel,
                                                   'ช่วงอภิปรายไม่ไว้วางใจ คุณไว้ใจทีมทำภารกิจนี้หรือไม่ พิมพ์ ผ่าน เพื่อให้ทีมนี้ไปทำภารกิจได้ พิมพ์ ไม่ผ่าน เพื่อไม่ให้ทีมนี้ไปทำภารกิจ',
                                                   expire_in=45)
            else:
                await client.safe_send_message(client.event_channel, message.author.mention + ' ไม่ใช่หัวหน้าภารกิจ อย่าเสือกค่ะ',
                                           expire_in=10, also_delete=message)
        elif command == 'ยืนยัน' and self.phase == AvalonGamePhase.TEAM_BUILDING:
            if message.author is self.players[self.leader_player_index]:
                if len(self.mission_team_members) == self.config['mission_players'][str(len(self.players))][str(self.round)]:
                    log.info('Change phase to TEAM_VOTING')
                    self.phase = AvalonGamePhase.TEAM_VOTING
                    for player in self.players:
                        self.votes_mission_team[player] = AvalonTeamVote.NONE
                    self.approve_team_vote_count = 0
                    self.reject_team_vote_count = 0
                    client.time = -1
                    await client.safe_send_message(client.event_channel,
                                                   'ช่วงอภิปรายไม่ไว้วางใจ คุณไว้ใจทีมทำภารกิจนี้หรือไม่ พิมพ์ ผ่าน เพื่อให้ทีมนี้ไปทำภารกิจได้ พิมพ์ ไม่ผ่าน เพื่อไม่ให้ทีมนี้ไปทำภารกิจ',
                                                   expire_in=45, also_delete=message)

                else:
                    await client.safe_send_message(client.event_channel, message.author.mention + ' คุณยังเลือกคนทำภารกิจไม่ครบ ตอนนี้มี ' + str(len(self.mission_team_members)) + ' คน')
            else:
                await client.safe_send_message(client.event_channel,
                                           message.author.mention + ' ไม่ใช่หัวหน้าภารกิจ อย่าเสือกค่ะ',
                                           expire_in=10, also_delete=message)

        elif command == 'ไม่เลือก' and self.phase == AvalonGamePhase.TEAM_BUILDING:
            one_member = None
            if message.author is self.players[self.leader_player_index]:
                for player in self.players:
                    if player.mentioned_in(message):
                        one_member = player
                        break

                if one_member in self.mission_team_members:
                    self.mission_team_members.remove(one_member)
                    await self.print_mission_memberlist(client)
                    await client.safe_delete_message(message)
                else:
                    await client.safe_send_message(client.event_channel,
                                                   message.author.mention + ' คนนี้ไม่อยู่ในทีมค่ะ อีโง่',
                                                   expire_in=5, also_delete=message)
            else:
                await client.safe_send_message(client.event_channel,
                                               message.author.mention + ' ไม่ใช่หัวหน้าภารกิจ อย่าเสือกค่ะ',
                                               expire_in=10, also_delete=message)

        elif command == 'ผ่าน' and self.phase == AvalonGamePhase.TEAM_VOTING:
            if message.author in self.players:
                if self.votes_mission_team[message.author] == AvalonTeamVote.REJECT:
                    self.reject_team_vote_count -= 1
                    self.approve_team_vote_count += 1
                else:
                    self.votes_mission_team[message.author] = AvalonTeamVote.APPROVE
                    self.approve_team_vote_count += 1

                if len(self.players) == (self.approve_team_vote_count + self.reject_team_vote_count):
                    await self.transition_from_voting(client)
                else:
                    vote_result = await self.print_vote_team_result()
                    if self.team_voting_message is not None:
                        await client.safe_delete_message(self.team_voting_message)
                    team_voting_msg_string = 'พิมพ์ ผ่าน เพื่อให้ทีมนี้ไปทำภารกิจได้ พิมพ์ ไม่ผ่าน เพื่อไม่ให้ทีมนี้ไปทำภารกิจ\n' + vote_result
                    team_voting_message = await client.safe_send_message(client.event_channel, team_voting_msg_string)
                    await client.safe_delete_message(message)
            else:
                await client.safe_send_message(client.event_channel,
                                               message.author.mention + ' ไม่ได้อยู่ในเกม อย่าเสือกค่ะ',
                                               expire_in=10, also_delete=message)
        elif command == 'ไม่ผ่าน' and self.phase == AvalonGamePhase.TEAM_VOTING:
            if message.author in self.players:
                if self.votes_mission_team[message.author] == AvalonTeamVote.APPROVE:
                    self.reject_team_vote_count += 1
                    self.approve_team_vote_count -= 1
                else:
                    self.votes_mission_team[message.author] = AvalonTeamVote.REJECT
                    self.reject_team_vote_count += 1

                if len(self.players) == (self.approve_team_vote_count + self.reject_team_vote_count):
                    await self.transition_from_voting(client)
                else:
                    vote_result = await self.print_vote_team_result()
                    if self.team_voting_message is not None:
                        await client.safe_delete_message(self.team_voting_message)
                    team_voting_msg_string = 'พิมพ์ ผ่าน เพื่อให้ทีมนี้ไปทำภารกิจได้ พิมพ์ ไม่ผ่าน เพื่อไม่ให้ทีมนี้ไปทำภารกิจ\n' + vote_result
                    team_voting_message = await client.safe_send_message(client.event_channel, team_voting_msg_string)
                    await client.safe_delete_message(message)
            else:
                await client.safe_send_message(client.event_channel,
                                               message.author.mention + ' ไม่ได้อยู่ในเกม อย่าเสือกค่ะ',
                                               expire_in=10, also_delete=message)

        elif command == 'ฆ่า' and self.phase == AvalonGamePhase.ENDING:
            if message.author in self.players:
                if self.roles[message.author] == AvalonRoles.ASSASSIN:
                    one_member = None
                    for player in self.players:
                        if player.mentioned_in(message):
                            one_member = player
                            break

                    if one_member is None:
                        await client.safe_send_message(client.event_channel,
                                                       message.author.mention + ' คนนี้ไม่อยู่ในเกมค่ะ อีโง่',
                                                       expire_in=5, also_delete=message)
                    else:
                        if self.roles[one_member] == AvalonRoles.MERLIN:
                            await self.game_over(client, is_good_win=False)
                        else:
                            await self.game_over(client, is_good_win=True)
                else:
                    await client.safe_send_message(client.event_channel,
                                                   message.author.mention + ' ไม่ใช่นักฆ่า อย่าเสือกค่ะ',
                                                   expire_in=10, also_delete=message)
            else:
                await client.safe_send_message(client.event_channel,
                                               message.author.mention + ' ไม่ได้อยู่ในเกม อย่าเสือกค่ะ',
                                               expire_in=10, also_delete=message)

    async def private_command(self, is_admin, client, message):
        log.info('Avalon: Private')
        message_content = message.content.strip()
        command, *args = message_content.split(
            ' ')  # Uh, doesn't this break prefixes with spaces in them (it doesn't, config parser already breaks them)
        command = command.lower().strip()
        args = ' '.join(args).lstrip(' ').split(' ')
        if command == 'ผ่าน' and self.phase == AvalonGamePhase.MISSION:
            if message.author in self.mission_team_members:
                log.info('Mission passed from ' + str(message.author.id))
                if self.votes_mission[message.author] == AvalonMissionVote.FAILED:
                    self.mission_failed_vote_count -= 1
                    self.mission_passed_vote_count += 1
                await client.safe_send_message(message.channel, 'คุณได้โหวตให้ภารกิจผ่านแล้ว', expire_in=0)

        elif command == 'ไม่ผ่าน' and self.phase == AvalonGamePhase.MISSION:
            if message.author in self.mission_team_members:
                user_role = self.roles[message.author]
                if user_role == AvalonRoles.MORDRED_MINION or user_role == AvalonRoles.ASSASSIN:
                    log.info('Mission failed from ' + str(message.author.id))
                    if self.votes_mission[message.author] == AvalonMissionVote.PASSED:
                        self.mission_failed_vote_count += 1
                        self.mission_passed_vote_count -= 1
                    await client.safe_send_message(message.channel, 'คุณได้โหวตให้ภารกิจล้มเหลวแล้ว', expire_in=0)
                else:
                    await client.safe_send_message(message.channel, 'คุณไม่สามารถโหวตให้ภารกิจล้มเหลวได้ เพราะคุณไม่ใช่สาวกของมาร์เตร็ด', expire_in=0)

    async def reset_game(self):
            self.players = []
            self.roles = {}
            self.round = 0

            self.votes_mission_team = {}
            self.votes_mission = {}
            self.mission_team_members = []

            self.evil_players = []
            self.approve_team_vote_count = 0
            self.reject_team_vote_count = 0
            self.mission_passed_vote_count = 0
            self.mission_failed_vote_count = 0

            self.phase = AvalonGamePhase.START
            self.failed_missions_count = 0
            self.leader_player_index = 0
            self.vote_reject_steak = 0


    async def print_playerlist(self, client):
        output_message = 'เกม Avalon พิมพ์ เล่น เพื่อร่วมเข้าเกม\nผู้เล่นในขณะนี้: \n'
        for player in self.players:
            output_message += player.mention + '\n'
        if self.playerlist is not None:
            await client.safe_delete_message(self.playerlist)
        self.playerlist = await client.safe_send_message(client.event_channel, output_message, expire_in=0)

    async def print_mission_memberlist(self, client):
        output_message = 'รายชื่อผู้เข้าทำภารกิจ:\n'
        for player in self.mission_team_members:
            output_message += player.mention + '\n'
        if self.team_building_memberlist_message is not None:
            await client.safe_delete_message(self.team_building_memberlist_message)
        self.team_building_memberlist_message = await client.safe_send_message(client.event_channel, output_message, expire_in=0)

    async def print_vote_team_result(self):
        output_message = 'ผลโหวต:\n'
        for player in self.votes_mission_team:
            output_message += player.mention
            if self.votes_mission_team[player] == AvalonTeamVote.APPROVE:
                output_message += ': ผ่าน\n'
            elif self.votes_mission_team[player] == AvalonTeamVote.REJECT:
                output_message += ': ไม่ผ่าน\n'
            elif self.votes_mission_team[player] == AvalonTeamVote.NONE:
                output_message += ': ยังไม่โหวต\n'
        return output_message

    async def transition_from_voting(self, client):
        log.info('Transition from Voting')
        approve_percentage = float(self.approve_team_vote_count) / float(len(self.players))
        if approve_percentage < 0.51:
            log.info('Mission Team Vote Failed')
            # voting failed
            await client.safe_send_message(client.event_channel,'โหวตทีมทำภารกิจไม่ผ่าน! กลับไปตั้งทีมใหม่', expire_in=40)
            self.vote_reject_steak += 1
            if self.vote_reject_steak == 5:
                await self.game_over(is_good_win=False)
            else:
                self.round += 1
                self.leader_player_index += 1
                self.phase = AvalonGamePhase.TEAM_BUILDING
                self.mission_team_members = []
                self.approve_team_vote_count = 0
                self.reject_team_vote_count = 0
                log.info('Change phase to TEAM_BUILDING')
                client.time = TEAM_BUILDING_TIME
                leader = self.players[self.leader_player_index]
                team_building_msg_string = 'ภารกิจที่ ' + str(self.round) + '\nหัวหน้าในการทำภารกิจครั้งนี้คือ ' + leader.mention + '\nพิมพ์ เลือก ตามด้วย @ ชื่อคนทีละคนเพื่อคัดเลือกคนเข้าทีมไปทำภารกิจ\nพิมพ์ ไม่เลือก ตามด้วย @ ชื่อคนทีละคน เพื่อนำคนออกจากทีมทำภารกิจ\nพิมพ์ ยืนยัน เพื่อยืนยันสมาชิกในทีมทำภารกิจ\nภารกิจนี้ต้องใช้ ' + str(self.config['mission_players'][str(len(self.players))][str(self.round)]) + ' คน\nผู้เล่นในขณะนี้: \n'
                for player in self.players:
                    team_building_msg_string += player.mention + '\n'
                self.team_building_message = await client.safe_send_message(client.event_channel, team_building_msg_string,
                                                                        expire_in=0)
        else:
            # voting success
            log.info('Mission Team Vote Sucess')
            await client.safe_send_message(client.event_channel, 'โหวตทีมทำภารกิจผ่านแล้ว! ผู้ที่ได้รับมอบหมายจงไปทำภารกิจให้เรียบร้อยภายในเวลา ' + str(MISSION_TIME) + ' วินาที',
                                           expire_in=MISSION_TIME)
            for player in self.mission_team_members:
                self.votes_mission[player] = AvalonMissionVote.PASSED
                if player.dm_channel is None:
                    await player.create_dm()

                await client.safe_send_message(player.dm_channel, 'ภารกิจที่ ' + str(self.round) + '\nพิมพ์ ผ่าน ในช่องนี้ เพื่อโหวตให้ภารกิจสำเร็จ พิมพ์ ไม่ผ่าน เพื่อโหวตให้ภารกิจล้มเหลว หากท่านปล่อยให้เวลาหมดจะถือว่าท่านโหวตให้ภารกิจผ่าน', expire_in=0)

            self.phase = AvalonGamePhase.MISSION
            log.info('Change phase to MISSION')
            client.time = MISSION_TIME
            self.mission_passed_vote_count = len(self.mission_team_members)
            self.mission_failed_vote_count = 0

    async def game_over(self, client, is_good_win):
        log.info('GAME OVER')
        self.phase = AvalonGamePhase.END
        roles_names = {
            AvalonRoles.ASSASSIN: 'นักฆ่า',
            AvalonRoles.MORDRED_MINION: 'สาวกของมอร์เดร็ด',
            AvalonRoles.MERLIN: 'เมอร์ลิน',
            AvalonRoles.ARTHUR_MINION: 'สมุนของอาเธอร์'
        }
        roles_list = ''
        for player in self.roles:
            roles_list += player.mention + ' : ' + roles_names[self.roles[player]] + '\n'

        if is_good_win:
            await client.safe_send_message(client.event_channel, 'ฝ่ายอาเธอร์ชนะ!\nเฉลยตำแหน่ง:\n' + roles_list, expire_in=0)
        else:
            await client.safe_send_message(client.event_channel, 'ฝ่ายมอร์เดร็ดชนะ!\nเฉลยตำแหน่ง:\n' + roles_list, expire_in=0)

        client.mode = BotMode.NONE
        await client.change_presence(activity=None)
        await self.reset_game()
        await client.reset_vote()
