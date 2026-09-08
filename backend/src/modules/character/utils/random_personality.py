import random

TRAITS = [
    "I always have a plan for what to do when things go wrong.",
    "I am confident in my abilities and I show it.",
    "I can find common ground with the fiercest enemy.",
    "I prefer animals over people.",
]

IDEALS = [
    "Honesty. I tell the truth no matter what.",
    "Freedom. Everyone should be free to direct their own destiny.",
    "Fairness. I do what is right, even if it is hard.",
    "Power. I want to be in charge of my own fate.",
]

BONDS = [
    "I protect those who cannot protect themselves.",
    "I will do anything to protect my hometown.",
    "Someone saved my life and I owe them a debt.",
    "My family means everything to me.",
]

FLAWS = [
    "I have a weakness for the vices of the city.",
    "I follow orders, even if I disagree.",
    "I am secretly afraid of failing and hide it.",
    "I trust almost anyone too easily.",
]


def _pick(items: list[str]) -> str:
    return random.choice(items)


def generate_random_personality() -> dict:
    return {
        "personality_traits": _pick(TRAITS),
        "ideals": _pick(IDEALS),
        "bonds": _pick(BONDS),
        "flaws": _pick(FLAWS),
    }