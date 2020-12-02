from abc import abstractmethod, ABC
from common_rules import *
import re
import random
import math

class Constant(object):
  def __init__(self, name, **props):
    self.name = name
    self.__dict__.update(props)
    
    globals()[name] = self

  def __repr__(self):
    return self.name

  def __str__(self):
    return self.name
    
class AssignRoles(SequenceElementRule):
  def get_options(self, g, advance):
    def _assign_roles():
      random.shuffle(g.players)
            
      g.send_public_message(
          "{} will decide whether to put the carrot in the box, then {} will choose whether to swap boxes.\n".format(g.players[0].name, g.players[1].name))
      advance()

    return {"Assign roles": _assign_roles}
      
    
class AskCarrot(SequenceElementRule):
  def set_initial_state(self, g):
    g.asked = None
    g.carrot = None
    
  def receive_private_message(self, g, sender, message, advance):
    if sender == g.players[0]:
      v = parse_yes_no(message)
      if v is None:
        g.send_private_message(sender, "Sorry, I don't understand")
        return True
      else:
        g.send_private_message(sender, "Got it")
        g.carrot = v
        advance()
        return True
    else:
      g.send_private_message(sender, "I'm busy right now")
      return True
    
  def get_options(self, g, advance):
    def _ask_about_carrot():
      g.asked = 0
      g.send_private_message(g.players[0],
        ":carrot: Would you like to put a carrot in the box we give to {}? Reply `Yes` or `No`.".format(
           g.players[1].name))
      g.send_public_message(
          ":envelope_with_arrow: **{} check your direct messages**.\n".format(g.players[0].name))

    if g.asked is not None:
      return {"Wait for reply": (lambda: None)}
    else:
      return {"Send private message about a carrot": _ask_about_carrot}


class AskBox(SequenceElementRule):
  def set_initial_state(self, g):
    g.swap = None
    
  def receive_public_message(self, g, sender, message, advance):
    if message == "!keep":
      if sender != g.players[1]:
        g.send_public_message("Only {} can make that decision".format(g.players[1].name))
        return True
      g.swap = False
      advance()
      return True
      
    if message == "!swap":
      if sender != g.players[1]:
        g.send_public_message("Only {} can make that decision".format(g.players[1].name))
        return True
      g.swap = True
      advance()
      return True
         
  def get_options(self, g, advance):
    def _ask_about_box():
      g.asked = 2
      g.send_public_message(
          "Hey {}, {} may or may not have put a carrot in your box.\n".format(g.players[1].name, g.players[0].name) +
          "You need to choose whether to keep your box or swap it.")
      g.send_public_message(
          "When you've made up your mind, reply `!keep` or `!swap`")
         
    if g.asked == 2:
      return {"Wait for reply": (lambda: None)}
    else:
      return {"Ask player 2 whether to swap the box": _ask_about_box}


class BigReveal(SequenceElementRule):
  def set_initial_state(self, g):
    g.revealed = False
    
  def get_options(self, g, advance):
    def _reveal_result():
      g.revealed = True
      g.send_public_message(
          "{} you chose to {} your box.\n".format(g.players[1].name, "swap" if g.swap else "keep"))
      if g.carrot:
        g.send_public_message(
            "I can reveal that {} put a carrot in your original box".format(g.players[0].name))
      else:
        g.send_public_message(
            "I can reveal that {} did not put a carrot in your original box".format(g.players[0].name))
                
      if g.carrot == g.swap:
        winner = g.players[0]
      else:
        winner = g.players[1]
        
      g.send_public_message(
          ":carrot::carrot::carrot: {} is the winner :carrot::carrot::carrot:".format(winner.name))
         
    if g.revealed:
      return {"Nothing to do": (lambda: None)}
    else:
      return {"Reveal the result": _reveal_result}

game_carrot = SequentialRule([
    AssignRoles(),
    AskCarrot(),
    AskBox(),
    BigReveal()
  ])
