from abc import abstractmethod, ABC
import re

class GameRule(ABC):
  def set_initial_state(self, g):
    pass
 
  def get_options(self, g):
    pass

  def receive_private_message(self, g, sender, message):
    return False
        
  def receive_public_message(self, g, sender, message):
    return False


class SequenceElementRule(ABC):
  def set_initial_state(self, g):
    pass
 
  def get_options(self, g, advance):
    pass

  def receive_private_message(self, g, sender, message, advance):
    return False
        
  def receive_public_message(self, g, sender, message, advance):
    return False
     
     
class ParallelRule(GameRule):
  def __init__(self, rules):
     self.subrules = rules
 
  def set_initial_state(self, g):
    for r in self.subrules:
       r.set_initial_state(g)
       
  def receive_private_message(self, g, sender, message):
    for r in self.subrules:
      handled = r.receive_private_message(g, sender, message)
      if handled:
        return handled
        
  def receive_public_message(self, g, sender, message):
    for r in self.subrules:
      handled = r.receive_public_message(g, sender, message)
      if handled:
        return handled

  def get_options(self, g): 
    ret = {}
    for r in self.subrules:
      o = r.get_options(g)
      if o:
        for (k, v) in o.items():
          ret[k] = v
    return ret    

RANDOM_WAIT_TIMER = "randomWait"

# useful for preventing savvy players from interring from how long stuff takes
class RandomWaitRule(SequenceElementRule):
  def __init__(self, duration_fn):
    self.duration_fn = duration_fn
  def get_options(self, g, advance): 
    def _start():
      g.start_timer(RANDOM_WAIT_TIMER, self.duration_fn())
      
    def _end():
      g.clear_timer(RANDOM_WAIT_TIMER)
      advance()
      
    if g.has_timer(RANDOM_WAIT_TIMER):
      if g.is_timer_expired(RANDOM_WAIT_TIMER):
        return {"Finish timer": _end}
      else:
        return {"Wait for timer": lambda:None}
    else:
      return {"Start wait": _start}
    
    
class SequentialRule(GameRule):
  """If any rule outputs no options, it will be skipped."""
  def __init__(self, rules, index_property="nightPosition"):
    self.rules = rules
    self.index_property = index_property
   
  def set_initial_state(self, g):
    setattr(g, self.index_property, 0)
    for r in self.rules:
      r.set_initial_state(g)

  def get_options(self, g): 
    position = getattr(g, self.index_property, 0)
    while True:
      if position >= len(self.rules):
        return None
      advance = lambda: setattr(g, self.index_property, position + 1)
      options = self.rules[position].get_options(g, advance)
      if options:
        return options
      else:
         position += 1
  
  def receive_private_message(self, g, sender, message): 
    position = getattr(g, self.index_property, 0)
    while True:
      if position >= len(self.rules):
        return None
      advance = lambda: setattr(g, self.index_property, position + 1)
      options = self.rules[position].get_options(g, advance)
      if options:
        return self.rules[position].receive_private_message(
            g, sender, message, advance)
      else:
         position += 1
         
  def receive_public_message(self, g, sender, message):
    position = getattr(g, self.index_property, 0)
    while True:
      if position >= len(self.rules):
        return None
      advance = lambda: setattr(g, self.index_property, position + 1)
      options = self.rules[position].get_options(g, advance)
      if options:
        return self.rules[position].receive_public_message(
            g, sender, message, advance)
      else:
         position += 1  
         
def parse_list_of_player_names(s, players):
  t = [x.strip() for x in re.split(",| and | ", s.lower()) if x.strip()]
  player_names = {p.name.lower(): p for p in players}
  r = []
  for x in t:
    if x in player_names:
      r.append(player_names[x])
    else:
      return None
  return r

def parse_yes_no(s):
  s = s.strip().lower()
  if s in ["yes", "y", "yeah", "sg"]: 
    return True
  elif s in ["no", "no way", "nope", "n",]:
    return False
  else:
    return None
