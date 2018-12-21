from enum import Enum

class SpyfallGamePhase(Enum):
    START = 1
    TALKING = 2
    ENDING = 3
    END = 4

class QuizGamePhase(Enum):
    START = 1

class WerewolfGamePhase(Enum):
    START = 1
    PREPARING = 2
    DAY = 3
    NIGHT = 4
    END = 5

class WerewolfRole(Enum):
    WEREWOLF = 1
    SEER = 2
    VILLAGER = 3
    DOCTOR = 4

class AvalonGamePhase(Enum):
    START = 1
    PREPARING = 2
    TEAM_BUILDING = 3
    TEAM_VOTING = 4
    MISSION = 5
    ENDING_ROUND = 6
    ENDING = 7
    END = 8

class AvalonRoles(Enum):
    MERLIN = 1
    PERCIVAL = 2
    ARTHUR_MINION = 3
    MORDRED = 4
    ASSASSIN = 5
    OBERON = 6
    MORGANA = 7
    MORDRED_MINION = 8

class AvalonTeamVote(Enum):
    APPROVE = 1
    REJECT = 2
    NONE = 3

class AvalonMissionVote(Enum):
    PASSED = 1
    FAILED = 2

class BotMode(Enum):
    NONE = 0
    SPYFALL = 1
    AVALON = 2
    WEREWOLF = 3
    QUIZ = 4
