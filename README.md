# Discord gamebot

Discord bot for running social games.

The bot supports:
* tracking the state of a game and enforcing rules
* sending and receiving public and private messages
* sending emoji reactions
* renaming players, e.g. to indicate their seating order in the game

It's mostly aimed at social-deception games, and includes one example implementation ('carrot in a box').

## Set up

1. Install python3
1. Register a discord bot account at the discord website. Create a server for it with a channel called `#general`.

1. Fill in your discord user id and server id in `discord_main.py`.

1. Create a file `~/discordsecret` containing your Discord API key.

1. Run `python3 discord_main.py`

## Usage 

Commands

* `!iam <name>` for players to claim a name
* `!who` to list players who have claimed a name
* `!carrot <player1>,<player2>` to start a new game of carrot in a box
* `!carrot test A,B` to start a new game of carrot in a box in a demo/test mode
* `!endgame`

## To implement your own game

Copy `game_carrot.py`. `common_rules.py` has some helpful classes for creating more
complex games. Game engines are a state-machine. There are three ways the state can be
mutated:

* `receive_public_message`, i.e. in response to public messages from players
* `receive_private_method`, i.e. in response to private messages from players
* `get_options`, which handles automatic progression of the game including timer-based events.
  This method should not mutate the state itself, but instead return lambdas that
  can mutate the state. If multiple lambdas are returned, one is chosen randomly.
  A prefix of "+" indicates a preferred action and a "-" an action of last resort.

## Notice

```
Copyright 2020 Ryan J. Lothian

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
