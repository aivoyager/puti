"""
@Author: obstacles
@Time:  2025-06-05 14:05
@Description:  
"""
from puti.llm.roles import Role
from puti.llm.envs import Env
from puti.llm.messages import Message


async def test_debate():
    # Debater
    Ethan = Role(name='Ethan', identity='Affirmative Debater')
    Olivia = Role(name='Olivia', identity='Opposition Debater')

    # create a debate contest and put them in contest
    env = Env(
        name='debate contest',
        desc="""Welcome to the Annual Debate Championship, a dynamic forum where critical thinking, persuasive speaking, and intellectual rigor converge.  This competition brings together talented debaters from diverse backgrounds to engage in structured argumentation on pressing contemporary issues.  Participants will compete in teams, presenting arguments for or against a given motion, while being judged on clarity, evidence, rebuttal strength, and overall delivery.
The goal of this debate is not only to win points but to foster respectful discourse, challenge assumptions, and inspire new perspectives.  Whether you are a passionate speaker or a curious listener, this event promises thought-provoking dialogue and high-level competition.
              """
    )
    env.add_roles([Ethan, Olivia])

    # topic
    topic = '科技发展是有益的还是有害的？ '

    # create a message start from Ethan
    msg = Message(content=topic, sender='user', receiver=Ethan.address)
    # Olivia needs user's input as background, but don't perceive it
    Olivia.rc.memory.add_one(msg)

    # then we publish this message to env
    env.publish_message(msg)

    # start the debate
    await env.run()

    # we can see all process from history
    print(env.history)


