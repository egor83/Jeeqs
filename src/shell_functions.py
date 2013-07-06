from models import *
# updates the challenge stats

all_challenge = Challenge.all().fetch(100)
for ch in all_challenge:
    ch.num_jeeqsers_submitted = Jeeqser_Challenge.all().filter('challenge = ', ch).count()
    ch.num_jeeqsers_solved = Attempt.query(Attempt.challenge == ch.key).filter(Attempt.status == AttemptStatus.SUCCESS).filter(Attempt.active == True).filter(Attempt.flagged == False).count()
    ch.put()
