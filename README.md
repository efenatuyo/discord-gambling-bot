# discord-gambling-bot


great gambling bot with funny responses (random responses)

## features

### logging
- will save every executed command in logs.txt

### random responses
- funny random response to every message (can be changed in config json)

## Commands

### beg
- random number between 0-1000
- Normal beg: random number * 1, chance 50%
- Super beg: random number * 2, chance 25%
- Advanced beg: random number * 4, chance 12.5%
- Millionaire beg: random number * 50, chance 1%

### profile
- will only show your balance

### leaderboard
- Will show top 10 (page 1) with most cash (global)
- You can scroll between pages
- Will display your rank on the footer and the current page

### give cash
- user will receive money from the person sending it
- if admin sends it (owner in config) there will be no cash removed and no checks done and the user will instantly get the money

### rob
- Rob players and earn their money
- Chance: if you got more money than the user you wanna rob it is 50% if you got less than 10% it is 10% if u got in range of 50 - 10 you get your chance rounded (user_you_wanna_rob / you)
- If you fail a rob you give a random amount of your money to the user you wanted to rob
- If you rob the user successfully you get a random amount of money from their balance
- both users need a min of 1000 cash

### gamble
- Roll a dice and if u got a higher number than the bot you dobble your money else you loose all the money you bet
- min 100 cash

### case_info
- display the chances of a case for winning cash

### open_case
- can choose which case (required)
- can choose amount of cases to open (not required, default 1, choices=[1, 2, 4])
- can choose if to play against bots (not required, default 0, choices=[1, 2, 4])
- if you play alone you win the amount you pulled
- if you played against bots you have to have the most value opened if so you win everyones items



this project will probally continue
