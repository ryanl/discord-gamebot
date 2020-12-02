from colors import *
import discord
import sys
import os.path
import random
from os.path import expanduser
import asyncio

from game_carrot import game_carrot
from game import *
import traceback

# fill in your user id here to get stacktraces pinged to you
OWNER_ID = 0000000000000000
# fill in your server id here
SERVER =   0000000000000000

class DiscordMessageQueuer(object):
  def __init__(self, client):
    self.renames = []
    self.private_message_queue = []
    self.public_message_queue = [] 
    self.client = client
    self.channel = None
    self.test_mode = False
    self.server = None
    self.summary_html = None
    self.summary_html_dirty = False
    
  def send_private_message(self, player, message):
    self.private_message_queue.append((player, message))    

  def send_public_message(self, message):
    self.public_message_queue.append(message)
    
  def set_player_nickname(self, player, nickname):
    self.renames.append((player, nickname))

  def set_game_summary_html(self, html):
    if html != self.summary_html:
      self.summary_html = html
      self.summary_html_dirty = True

  def fyi(self, message):
    print(BLUE + "  [FYI to storyteller] " + message + RESET)
    if self.test_mode:
      self.public_message_queue.append(":envelope:  " + message)

  async def get_server(self):
    if not self.server:
      self.server = self.client.get_guild(self.client.server_id)
    return self.server
    
  async def get_channel(self):
    if not self.channel:
      self.server = await self.get_server()
      self.channel = discord.utils.get(self.server.text_channels, name=self.client.channel_name)
      print("Channel for #{} is {}".format(self.client.channel_name, self.channel.id))
    return self.channel
            
  async def send_messages(self):
    if self.summary_html_dirty:
      # You can add code to upload to a website here, if you like
      self.summary_html_dirty = False
    
    self.channel = await self.get_channel()
    while self.renames:
      (p, n) = self.renames.pop(0)
      print("Renaming {} to {}".format(p.name, n))
      try:
        member = await self.server.fetch_member(self.client.iams[p.name])
        if member.nick != n:
          await member.edit(nick=n)
      except:
        # name may not exist in iams if we are in test mode
        if p.name in self.client.iams:
          self.public_message_queue.append( 
              "<@!{}> please change your nickname to `{}`".format(
                  self.client.iams[p.name], 
                  n))

    if self.public_message_queue:
      while self.public_message_queue:
        m = self.public_message_queue.pop(0)
        if m.startswith("/tts"):
          m = m[len("/tts"):].strip()
          tts = True
        else:
          tts = False
        print(GREEN + m + RESET)
        await self.channel.send(m, tts=tts)
          
    while self.private_message_queue: 
      (p, m) = self.private_message_queue.pop(0)
      if isinstance(p, str):
        name = p
      else:
        name = p.name
               
      if self.test_mode:
        await self.channel.send("{} << {}".format(name, m))
      else:
        if name in self.client.iams:
          u = self.client.get_user(self.client.iams[name])
          # get_user hits a cache
          if u is None:
            u = await self.client.fetch_user(self.client.iams[name])
          print(BLUE + name + " << " + m + RESET)
          await u.send(m)
        else:
          raise ValueError("Unknown private message target {}".format(name))


class AvailableGame(object):
  def __init__(self, verb, rule, min_players, max_players):
    self.verb = verb
    self.rule = rule
    self.min_players = min_players
    self.max_players = max_players


class DiscordInterface(discord.Client):
  
  def __init__(self, server_id, channel_name, available_games):
    super().__init__()
    self.server_id = server_id
    self.channel_name = channel_name
    self.channel_id = None
    self.iams = {}
    self.game = None
    self.send_queue = DiscordMessageQueuer(self)
    self.available_games = available_games
      
  def go(self):
    with open(os.path.join(expanduser("~"), "discordsecret")) as f:
      secret = f.read().strip()
    self.run(secret)
  
  async def _handle_iam(self, message):
    m = message.content
    if self.game:
      self.send_queue.send_public_message("You can't pick your name during a game")
      return
       
    name = m.split(" ", 1)[1]
    if not name:
      self.send_queue.send_public_message(
          "<@!{}>: Name must be at least 1 letter long".format(message.author.id))
      return
    valid_chars = "0123456789abcdefghijklmnopqrstuvwyxzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
    for c in name:
      if c not in valid_chars:
       self.send_queue.send_public_message(
           "<@!{}>: Only alphanumeric and _ characters are allowed in your name"
               .format(message.author.id))
       return
    previous = None
    for p in self.iams:
      if self.iams[p] == message.author.id:
        previous = p
        del self.iams[p]
        break
    for p in self.iams: 
      if p.lower() == name.lower():
        self.send_queue.send_public_message("<@!{}>: name {} is already taken by <@!{}>".format(
            message.author.id, name, self.iams[p]))
        return 
    self.iams[name] = message.author.id
    await message.add_reaction("✅")
    
    # save
    with open("iams", "w") as f:
      for (k, v) in self.iams.items():
        f.write("{} {}\n".format(k, v))

  async def _handle_who(self, voice_only=False):
    m = []
    c = await self.send_queue.get_channel()
    async with c.typing():
      server = await self.send_queue.get_server() 
      if voice_only:
        voice_ids = {m.id for v in server.voice_channels for m in v.members}
        players = [n for (n,i) in self.iams.items() if i in voice_ids]
      else:
        players = [p for p in self.iams]
      members = await asyncio.gather(*[server.fetch_member(self.iams[p]) for p in players])
      for (p, member) in zip(players, members):
        if member:
          n = member.display_name
        else:
          n = "unknown"
        m.append("{} is **{}**".format(p, n))
      if m:
        self.send_queue.send_public_message("\n".join(m))
      else:
        self.send_queue.send_public_message("None")

  async def _handle_endgame(self, message):
    if self.game:
      await message.add_reaction("✅")
      self.send_queue.send_public_message("Game concluded.")
      self.game = None
      self.send_queue.test_mode = False
    else:
      self.send_queue.send_public_message("<@!{}> No game in progress.".format(message.author.id))
          
  def _handle_new_game(self, available_game, message):
    m = message.content
    if self.game:
      self.send_queue.send_public_message("<@!{}> To start a new game, first use `!endgame`".format(message.author.id))
      return
    if m.strip() == available_game.verb:
      self.send_queue.send_public_message("Specify players: e.g. `{} Player1,...`"
          .format(available_game.verb))
      return

    splitm = m.split()[1:]
    if splitm[0] == "test":
      self.send_queue.test_mode = True
      splitm = splitm[1:]
    else:
      self.send_queue.test_mode = False
    
    players = list(set(x.strip() for x in splitm[0].split(",")))
    if len(players) < available_game.min_players or len(players) > available_game.max_players:
      self.send_queue.send_public_message(
          "Syntax `{} Player1,...`\n{}-{} players supported."
              .format(
                  available_game.verb,
                  available_game.min_players,
                  available_game.max_players))
      return 
    
    for name in players: 
      if name not in self.iams and not self.send_queue.test_mode:
        self.send_queue.send_public_message(
            "I don't know who {} is. They'll need to use `!iam <name>` to register".format(name))
        return
    
    random.shuffle(players)
    self.game = GameState(
      players = [PlayerState(name=n, id=self.iams.get(n)) for n in players],
      rule = available_game.rule,
      sender = self.send_queue
    )
    self.send_queue.send_public_message(
        "Starting a new game for {} players: {}".format(
            len(players), 
            ", ".join(players)))
    # TODO: rename players not playing
    if self.send_queue.test_mode:
      self.send_queue.send_public_message(
        "Test mode enabled. All messages will be sent and received publicly. Syntax:\n" +
        "`Scott >> this is a private message Scott sends`\n" +
        "`Jess !! this is a public message Jess sends`")

  async def tick_task(self): 
    while True:
      try:
        if self.game:
          actions = list(self.game.validActions())
          actions_encouraged = [a for a in actions if a.startswith("+")]
          actions_excluding_discouraged = [a for a in actions if not a.startswith("-")]
          
          if actions_encouraged:
            a = random.choice(actions_encouraged)
            print("Taking encouraged action {}".format(a))
            self.game.takeAction(a)
          elif actions_excluding_discouraged:
            a = random.choice(actions_excluding_discouraged)
            print("Taking action {}".format(a))
            self.game.takeAction(a)
          else:
            print("No actions available at state {}".format(self.game))
            
        await self.send_queue.send_messages()
      except Exception as e:
        ry = self.get_user(OWNER_ID)
        await ry.send("```" + traceback.format_exc() + "```")
        print(RED + traceback.format_exc() + RESET)
      await asyncio.sleep(random.random() + random.random() + 0.5)
  

  async def on_ready(self):
    print('Logged on as {0}!'.format(self.user))
    self.loop.create_task(self.tick_task())
    self.loop.create_task(upload_file("content.html", "<html><body>No game in progress</body></html>"))

  async def process_commands_that_ignore_test_mode(self, message):
    private_message = isinstance(message.channel, discord.DMChannel)
    m = message.content.strip()
    if private_message:
      if m.startswith("!saypublic ") and message.author.id == OWNER_ID:
        # admin command
        self.send_queue.send_public_message(m.split(" ", 1)[1])
        await message.add_reaction("✅")
      elif m.startswith("!sayprivate ") and len(m.split(" ")) > 2 and message.author.id == OWNER_ID: 
        # admin command
        _, target, pm = m.split(" ", 2)
        if target not in self.iams.keys():
          self.send_queue.send_private_message(player_name,  "Target not recognized")
        else:
          self.send_queue.send_private_message(target, pm)
          await message.add_reaction("✅")
    if m == "!who":
      await self._handle_who()
    if m == "!whohere":
      await self._handle_who(voice_only=True)
    elif m.lower().startswith("!iam "):
      await self._handle_iam(message)
    elif m == "!endgame":
      await self._handle_endgame(message)
    elif m == "!error":
      raise ValueError("intentional error")
    else:
      if m:
        verb = m.split()[0]
      else:
        verb = ""
      for a in self.available_games:
        if verb == a.verb:
          self._handle_new_game(a, message)
          return
          
  async def process_message(self, message):
    if message.author.id == self.user.id:
      return
    # Ignore stuff on the #feedback channel
    if not isinstance(message.channel, discord.DMChannel) and message.channel.name != self.channel_name:
      return
      
    await self.process_commands_that_ignore_test_mode(message)
    player_name = None
    if self.send_queue.test_mode:
      if not isinstance(message.channel, discord.DMChannel):
        if ">>" in message.content:
          player_name, m = [x.strip() for x in message.content.split(">>", 1)]
          print('Faking private from {}: {}'.format(player_name, m))
          private_message = True
        elif "!!" in message.content:
          player_name, m = [x.strip() for x in message.content.split("!!", 1)]
          print('Faking public from {}: {}'.format(player_name, m))
          private_message = False
    else:
      private_message = isinstance(message.channel, discord.DMChannel)
      m = message.content    
      if message.author.id in self.iams.values():
        player_name = [k for (k,v) in self.iams.items() if v == message.author.id][0]
      else:
        player_name = None
      
      print('Private from {0.author}: {0.content}'.format(message))
    
    if self.game:
      if player_name and player_name in [p.name for p in self.game.players]:
        if private_message:
          result = self.game.receive_private_message(player_name, m)
          if isinstance(result, str): 
            await message.add_reaction(result)
        else:
          result = self.game.receive_public_message(player_name, m)
          if isinstance(result, str): 
            await message.add_reaction(result)
      else:
        print("Ignoring message from unknown sender {}".format(message.author))
    else:
      print('Message from {0.author} on {0.channel}: {0.content}'.format(message))
            
  async def on_message(self, message):
    try:
      await self.process_message(message)
      await self.send_queue.send_messages()
    except Exception as e:
      ry = self.get_user(OWNER_ID)
      await ry.send("```" + traceback.format_exc() + "```")
      await message.add_reaction("💥")
      print(RED + traceback.format_exc() + RESET)


def main():
  if len(sys.argv) != 1:
    print_usage()
    sys.exit(1)
    
  d = DiscordInterface(
      server_id=SERVER,
      channel_name="general",
      available_games=[
          AvailableGame(verb="!carrot", rule=game_carrot, min_players=2, max_players=2),
      ])
  # load
  if os.path.exists("iams"):
    with open("iams", "r") as f:
      iams = {}
      for line in f:
        (k,v) = line.split()
        iams[k] = int(v)
      d.iams = iams

  d.go()
          
if __name__ == "__main__":
  main()
