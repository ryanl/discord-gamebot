from colors import *
import sys
import os.path
import random
import time


class PlayerState(object):
  def __init__(self, name, **initial_state):
     self.__dict__ = initial_state
     self.name = name
     
  def __repr__(self):
    return "PlayerState({})".format(
       ",".join(["{}={}".format(k, v) for (k, v) in self.__dict__.items() if v]))


class GameState(object):
  def __init__(self, players, rule, sender, time_source_secs=time.time, **initial_state):
    self.__dict__ = initial_state
    self.players = players
    self.rule = rule
    self.rule.set_initial_state(self)
    self.sender = sender
    self.timers = {}
    self.time_source_secs = time_source_secs

  def set_sidebar_channels(self, channels):
    pass
    # TODO: implement this
    # self.sender.set_sidebar_channels(channels)

  def send_public_message(self, message):
    self.sender.send_public_message(message)
      
  def send_private_message(self, player_or_players, message):
    if isinstance(player_or_players, list):
      for p in player_or_players: 
        send_private_message(p, message)
    else:
      p = player_or_players
      if isinstance(p, str):
        p = self.getPlayerByName(p)
      self.sender.send_private_message(p, message)
  
  def receive_private_message(self, player, message):
    if isinstance(player, str):
      name = player
      player = self.getPlayerByName(player)
      if not player:
        raise ValueError("No player with name {}".format(name))
    return self.rule.receive_private_message(self, player, message)

  def receive_public_message(self, player, message):
    if isinstance(player, str):
      name = player    
      player = self.getPlayerByName(player)
      if not player:
        raise ValueError("No player with name {}".format(name))
    return self.rule.receive_public_message(self, player, message)

  def set_game_summary_html(self, html):
    self.sender.set_game_summary_html(html)
  
  def fyi(self, message):
    self.sender.fyi(message)

  def start_timer(self, timer_name, secs):
    self.timers[timer_name] = self.time_source_secs() + secs

  def clear_timer(self, timer_name):
    if timer_name in self.timers:
      del self.timers[timer_name]
 
  def get_timers(self):
    return self.timers.keys()

  def get_remaining_time(self, timer_name):
    if not self.has_timer(timer_name):
      return 0
    else:
      return self.timers[timer_name] - self.time_source_secs()

  def has_timer(self, timer_name):
    return timer_name in self.timers
    
  def is_timer_expired(self, timer_name):
    return self.has_timer(timer_name) and self.time_source_secs() > self.timers[timer_name]
  
  def set_player_nickname(self, player, nickname):
    self.sender.set_player_nickname(player, nickname)

  def __repr__(self):
    s = ["GameState("]
    s.append("  players=[")
    for p in self.players:
      s.append("    {}".format(p))     
    s.append("]")
    for (k,v) in self.__dict__.items():
      if k not in ("rule", "sender", "time_source_secs", "players"):
        s.append("  {}={}".format(k, v))
    s.append(")")
    return "\n".join(s)

  def getPlayerByName(self, name): 
    for p in self.players:
      if p.name.lower().strip() == name.lower().strip():
        return p
    return None
    
  def _validActions(self):
    return self.rule.get_options(self)
    
  def validActions(self):
    v = self._validActions()
    if v:
      if not isinstance(v, dict):
        print("Unexpected non-dict actions: ", v)
        return ["There are no valid actions right now"]        
      return v.keys()
    else:
      return ["There are no valid actions right now"]
      
  def takeAction(self, a):
    if a == "There are no valid actions right now": 
      return
    actions = self._validActions()
    if a not in actions:
      print("Action not valid (did a timer happen?): {}".format(a))
    else:
      actions[a]()

