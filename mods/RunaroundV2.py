#Made by Froshlee14 
import bs
import random

def bsGetAPIVersion():
    return 4

def bsGetGames():
    return [Runaround2Game]

class Runaround2Game(bs.TeamGameActivity):

    @classmethod
    def getName(cls):
        return 'Runaround V2'

    @classmethod
    def getDescription(cls,sessionType):
        return ('Reach the exit.')

    @classmethod
    def supportsSessionType(cls,sessionType):
        return True if (issubclass(sessionType,bs.TeamsSession)
                        or issubclass(sessionType,bs.FreeForAllSession)) else False

    @classmethod
    def getSupportedMaps(cls,sessionType):
        return ['Tower D']

    @classmethod
    def getSettings(cls,sessionType):
        return [("Score to Win Per Player",{'minValue':1,'default':5,'increment':1}),
                ("Equip Shield",{'default':False}),
                ("Max bots",{'minValue':2,'maxValue':20,'default':4,'increment':1}),
                ("Time Limit",{'choices':[('None',0),('1 Minute',60),
                                        ('2 Minutes',120),('5 Minutes',300),
                                        ('10 Minutes',600),('20 Minutes',1200)],'default':0}),
                ("Respawn Times",{'choices':[('Shorter',0.25),('Short',0.5),('Normal',1.0),('Long',2.0),('Longer',4.0)],'default':1.0}),
                ("Epic Mode",{'default':False})]


    def __init__(self,settings):
        bs.TeamGameActivity.__init__(self,settings)
        if self.settings['Epic Mode']: self._isSlowMotion = True
        # print messages when players die since it matters here..
        self.announcePlayerDeaths = True        

        self._scoreBoard = bs.ScoreBoard()

        self._scoreRegionMaterial = bs.Material()
        self._scoreRegionMaterial.addActions(
            conditions=("theyHaveMaterial",bs.getSharedObject('playerMaterial')),
            actions=(("modifyPartCollision","collide",True),
                     ("modifyPartCollision","physical",False),
                     ("call","atConnect", self._onPlayerScores)))

        self._safeRegionMaterial = bs.Material()
        self._safeRegionMaterial.addActions(
            conditions=("theyHaveMaterial",bs.Bomb.getFactory().bombMaterial),
            actions=(("modifyPartCollision","collide",True),
                     ("modifyPartCollision","physical",True)))
        
    def getInstanceDescription(self):
        return ('Score ${ARG1} points to win.',self._scoreToWin)

    def getInstanceScoreBoardDescription(self):
        return ('Score ${ARG1} points to win',self._scoreToWin)

    def onTransitionIn(self):
        bs.TeamGameActivity.onTransitionIn(self, music='Epic' if self.settings['Epic Mode'] else 'GrandRomp')

    def onTeamJoin(self,team):
        team.gameData['score'] = 0
        if self.hasBegun(): self._updateScoreBoard()

    def onBegin(self):
        bs.TeamGameActivity.onBegin(self)
        self.setupStandardTimeLimit(self.settings['Time Limit'])
        self._scoreToWin = self.settings['Score to Win Per Player']
        self._updateScoreBoard()
        self._scoreSound = bs.getSound('dingSmall')
        self._cheerSound = bs.getSound("cheer")

        self._scoreRegions = []
        defs = self.getMap().defs
        self._scoreRegions.append(bs.NodeActor(bs.newNode('region',
                                                          attrs={'position':defs.boxes['scoreRegion'][0:3],
                                                                 'scale':defs.boxes['scoreRegion'][6:9],
                                                                 'type': 'box',
                                                                 'materials':(self._scoreRegionMaterial,)})))

        self._scoreRegions.append(bs.NodeActor(bs.newNode('region',
                                                          attrs={'position':(-9.000552706, 3.1524, 0.3095359717),
                                                                 'scale':(2.5, 4.0, 1.1),
                                                                 'type': 'box',
                                                                 'materials':(self._safeRegionMaterial,)})))

        self._bots = bs.BotSet()
        for i in range(self.settings['Max bots']):
         bs.gameTimer(1000,bs.Call(self._bots.spawnBot,bs.BomberBotProStatic,pos=self.getRandomBotPoint(),spawnTime=0))
 
        self._updateTimer = bs.Timer(1000,self._onSpazBotDied,repeat=True)
      
    def spawnPlayer(self,player):
        pos = self.getMap().defs.points['botSpawnStart']
        spaz = self.spawnPlayerSpaz(player,position=pos)

        #The players cant jump, and run.
        spaz.connectControlsToPlayer(enablePunch=False,
                                     enableBomb=False,
                                     enablePickUp=False,
                                     enableRun=False,
                                     enableJump=False)
        if self.settings['Equip Shield']: player.actor.handleMessage(bs.PowerupMessage('shield'))

    def _flash(self,pos,player,length=1000):
        light = bs.newNode('light',
                           attrs={'position':pos,
                                  'heightAttenuated': False,
                                  'radius':0.2,
                                  'color': player.color})
        bs.animate(light,"intensity",{0:0,100:2.0,500:0},loop=False)
        bs.gameTimer(length,light.delete)

    def getRandomBotPoint(self):
        p1 = self.getMap().defs.points['tntLoc'][0:3]
        p2 = self.getMap().defs.points['botSpawnBottomLeft'][0:3]
        p3 = self.getMap().defs.points['botSpawnBottomRight'][0:3]
        p4 = self.getMap().defs.points['ffaSpawn1'][0:3]
        p5 = self.getMap().defs.points['powerupSpawn1']
        p6 = self.getMap().defs.points['powerupSpawn2']
        p7 = self.getMap().defs.points['powerupSpawn3']
        p8 = self.getMap().defs.points['powerupSpawn4']
        p9 = self.getMap().defs.points['shadowLowerTop']
        return (random.choice([p1,p2,p3,p4,p5,p6,p7,p8,p9]))

    def _getRandomBotType(self):
        bt = [bs.BomberBotProStatic,
                  bs.BomberBotProStatic,
                  bs.ChickBot,
                  bs.BomberBotProStatic,
                  bs.BomberBotProStatic,
                  bs.MelBot,
                  bs.BomberBotProStatic,
                  bs.BomberBotProStatic]
        return (random.choice(bt))

    def _onPlayerScores(self):
        regionNode,playerNode = bs.getCollisionInfo('sourceNode','opposingNode')
        try: player = playerNode.getDelegate().getPlayer()
        except Exception: player = None
        region = regionNode.getDelegate()
        if player.exists() and player.isAlive():
         player.getTeam().gameData['score'] = max(0,player.getTeam().gameData['score']+1)
         bs.playSound(self._scoreSound)
         pos = player.actor.node.position
         self._flash(pos,player)
         self._updateScoreBoard()

         newPos = self.getMap().defs.points['botSpawnStart']
         player.actor.handleMessage(bs.StandMessage(newPos))
         player.actor.handleMessage(bs.PowerupMessage('health'))
         if self.settings['Equip Shield']: player.actor.handleMessage(bs.PowerupMessage('shield'))

         try: player.actor.node.handleMessage('celebrate',1500)
         except Exception: pass

         if any(team.gameData['score'] >= self._scoreToWin for team in self.teams):
          self._bots.stopMoving()
          self._bots.finalCelebrate()
          bs.playSound(self._cheerSound)
          bs.gameTimer(500,self.endGame)                

    def handleMessage(self,m):
        if isinstance(m,bs.PlayerSpazDeathMessage):
            bs.TeamGameActivity.handleMessage(self,m) # augment standard behavior
            player = m.spaz.getPlayer()
            self.respawnPlayer(player)

        elif isinstance(m,bs.SpazBotDeathMessage):
            self._onSpazBotDied(m)
            bs.TeamGameActivity.handleMessage(self,m)  
        else:
            # default handler:
            bs.TeamGameActivity.handleMessage(self,m)

    #Because the bots are very dumbs
    def _onSpazBotDied(self,DeathMsg):
        self._bots.spawnBot(self._getRandomBotType(),pos=self.getRandomBotPoint(),spawnTime=2000)

    def _updateScoreBoard(self):
        for team in self.teams:
            self._scoreBoard.setTeamValue(team,team.gameData['score'],self._scoreToWin)

    def endGame(self):
        results = bs.TeamGameResults()
        for t in self.teams: results.setTeamScore(t,t.gameData['score'])
        self.end(results=results)