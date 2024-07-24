import time
import random
from typing import Literal


class Constants:
    """Helper class containing numeric constants used by gameplay mechanics."""

    # Euler–Mascheroni constant, used for calculating approximate level XP requirements.
    gamma = 0.57721566490153286060


class GameType(object):
    """Base class used for representation of all in-game objects. All GameTypes have a name, description,
    and an indefinite article matching the name."""

    def __init__(
        self,
        type_name,
        type_description: None | str,
        indefinite_article: None | Literal["a", "an"] = None,
    ):
        # GameTypes have attributes, at minimum:
        #   1. Type Name - type_name: the type's displayed text name
        #   2. Type Description - type_description: the type's displayed text description
        #   3. Indefinite article - indefinite_article: the type's displayed indefinite article
        assert isinstance(type_description, str)
        assert type_description.isascii()
        assert (indefinite_article is None) or isinstance(indefinite_article, str)

        # 1. Type Name - The type's name.
        # Typically, this is the subclass' class name obtained via self.__class__.__name__.
        self.type_name = type_name

        # 2. Description - A succinct description of the type.
        if type_description is None:
            self.type_description = "Missing description!"

        if type_description.endswith((".", "?", "!")):
            self.type_description = type_description
        else:
            self.type_description = type_description + "."

        # 3. Indefinite Article - an appropriate indefinite article ("a" or "an") for the type name.
        if indefinite_article is None:
            # No indefinite article provided, try to guess it.
            # NOTE: Will produce incorrect output for words like "Herb" and "Unicorn"
            if self.type_name.lower().startswith(("a", "e", "i", "o", "u")):
                self.indefinite_article = "an"
            else:
                self.indefinite_article = "a"
        else:
            self.indefinite_article = indefinite_article

    def __str__(self):
        return f"{self.indefinite_article.capitalize()} {self.type_name}. {self.type_description.capitalize()}"

    def __repr__(self):
        return f'{self.type_name}("{self.type_name}", "{self.type_description}", indefinite_article="{self.indefinite_article}")'


class Skills:
    class Constants:
        class Numeric:
            MAX_XP = 200_000_000
            MAX_LEVEL = 99
            MIN_XP = 0
            MIN_LEVEL = 1

        class String:
            AGILITY = "Agility"
            FIREMAKING = "Firemaking"
            FLETCHING = "Fletching"
            ATTACK = "Attack"
            WOODCUTTING = "Woodcutting"
            PRAYER = "Prayer"
            MAGIC = "Magic"
            RANGED = "Ranged"
            CRAFTING = "Crafting"
            DEFENCE = "Defence"
            STRENGTH = "Strength"
            HERBLORE = "Herblore"
            SMITHING = "Smithing"
            CONSTRUCTION = "Construction"
            COOKING = "Cooking"
            RUNECRAFT = "Runecraft"
            HITPOINTS = "Hitpoints"
            SLAYER = "Slayer"
            MINING = "Mining"
            HUNTER = "Hunter"
            THIEVING = "Thieving"
            FARMING = "Farming"
            FISHING = "Fishing"

        class Container:
            # Set of all Skill names
            SKILL_NAMES: set[str] = {
                "Attack",
                "Strength",
                "Defence",
                "Ranged",
                "Prayer",
                "Magic",
                "Runecraft",
                "Construction",
                "Hitpoints",
                "Agility",
                "Herblore",
                "Thieving",
                "Crafting",
                "Fletching",
                "Slayer",
                "Hunter",
                "Mining",
                "Smithing",
                "Fishing",
                "Cooking",
                "Firemaking",
                "Woodcutting",
                "Farming",
            }

            # Level-to-XP LUT (from: https://oldschool.runescape.wiki/w/Experience#Formula)
            LEVEL_XP: list[int] = [
                0,  # Level 0, index 0
                0,  # Level 1, index 1
                *(
                    int(
                        round(
                            1
                            / 8
                            * (
                                level**2
                                - level
                                + 600
                                * (2 ** (level / 7) - 2 ** (1 / 7))
                                / (2 ** (1 / 7) - 1)
                            )
                            - level / 10
                            - Constants.gamma
                        )
                    )
                    for level in range(2, 127)
                ),
            ]

    class Skill(GameType):
        @staticmethod
        def level_from_xp(xp: int) -> int:
            """Returns the level attained by a ``Skill`` with ``xp`` experience points."""
            bounds_l, bounds_r = (
                Skills.Constants.Numeric.MIN_LEVEL,
                Skills.Constants.Numeric.MAX_LEVEL,
            )

            while bounds_l <= bounds_r:
                m = (bounds_l + bounds_r) // 2
                level_plus_zero_xp, level_plus_one_xp = (
                    Skills.Constants.Container.LEVEL_XP[m],
                    Skills.Constants.Container.LEVEL_XP[m + 1],
                )
                if level_plus_zero_xp <= xp < level_plus_one_xp:
                    return m
                if xp >= level_plus_one_xp:
                    bounds_l = m + 1
                if xp < level_plus_zero_xp:
                    bounds_r = m - 1
            raise RuntimeError

        @staticmethod
        def xp_from_level(level: int) -> int:
            """Returns the minimum experience points attained by a ``Skill`` at ``level``."""
            assert isinstance(level, int)
            assert (
                Skills.Constants.Numeric.MAX_LEVEL
                <= level
                <= Skills.Constants.Numeric.MAX_LEVEL
            )
            return Skills.Constants.Container.LEVEL_XP[level]

        def __init__(
            self,
            name: str,
            xp: int = 0,
            description="This skill lacks a description!",
            indefinite_article=None,
        ):
            # Name must be a valid skill name
            assert isinstance(name, str)
            assert name.capitalize() in Skills.Constants.Container.SKILL_NAMES

            # Valid XP values are (0, 200,000,000)
            assert isinstance(xp, int)
            assert (
                Skills.Constants.Numeric.MIN_XP <= xp <= Skills.Constants.Numeric.MAX_XP
            )

            super().__init__(name, description, indefinite_article)

            # Skill levels are derived from the accumulated XP
            self.xp = xp
            self.level = self.get_level()

        def get_level(self) -> int:
            """Returns the current level of the Skill."""
            return self.level_from_xp(self.xp)

        def set_level(self, new_level: int) -> int:
            """Sets ``self.level`` equal to ``new_level``.

            Returns the new level value.

            **Side effect**: *will* modify ``self.xp``.
            :raise AssertionError:"""
            assert isinstance(new_level, int)
            assert (
                Skills.Constants.Numeric.MIN_LEVEL
                <= new_level
                <= Skills.Constants.Numeric.MAX_LEVEL
            )
            self.xp = Skills.Constants.Container.LEVEL_XP[new_level]
            self.level = new_level
            return self.level

        def level_up(self) -> int:
            """Increments ``self.level`` by one.

            Returns the new level value.

            **Side effect**: *will* modify ``self.xp``.
            :raise AssertionError:"""
            new_level = self.level + 1
            assert new_level <= Skills.Constants.Numeric.MAX_LEVEL
            self.xp = Skills.Constants.Container.LEVEL_XP[new_level]
            self.level = new_level
            return new_level

        def set_xp(self, new_xp: int) -> int:
            """Sets ``self.xp`` equal to ``new_xp``.

            Returns the new quantity of experience points.

            **Side effect**: *may* modify ``self.level``.
            :raise AssertionError:"""
            assert isinstance(new_xp, int)
            assert (
                Skills.Constants.Numeric.MIN_XP
                <= new_xp
                <= Skills.Constants.Numeric.MAX_XP
            )
            self.xp = new_xp
            self.level = self.get_level()
            return self.xp

        def modify_xp(self, delta: int) -> int:
            """Adds ``delta`` to ``self.xp``.

            Returns the new quantity of experience points.

            **Side effect**: *may* modify ``self.level``.
            :raise AssertionError:"""
            assert isinstance(delta, int)
            assert (
                Skills.Constants.Numeric.MIN_XP
                <= self.xp + delta
                <= Skills.Constants.Numeric.MAX_XP
            )
            self.xp += delta
            self.level = self.get_level()
            return self.xp

        def add_xp(self, amount: int) -> int:
            """Adds ``amount`` experience points to ``self.xp``

            Returns the new quantity of experience points.

            **Side effect**: *may* modify ``self.level``"""
            assert isinstance(amount, int)
            delta = abs(amount)
            return self.modify_xp(delta)

        def subtract_xp(self, amount) -> int:
            """Subtracts ``amount`` experience points from ``self.xp``

            Returns the new quantity of experience points.

            **Side effect**: *may* modify ``self.level``"""
            assert isinstance(amount, int)
            delta = -1 * abs(amount)
            return self.modify_xp(delta)

    class SkillSet(object):
        """Helper structure to organize Skill objects"""

        def __init__(self, descriptor: None | dict[str, int] = None):
            self.agility = Skills.Skill(
                "Agility", 0, "Agility - placeholder description!"
            )
            self.attack = Skills.Skill("Attack", 0, "Attack - placeholder description!")
            self.construction = Skills.Skill(
                "Construction", 0, "Construction - placeholder description!"
            )
            self.cooking = Skills.Skill(
                "Cooking", 0, "Cooking - placeholder description!"
            )
            self.crafting = Skills.Skill(
                "Crafting", 0, "Crafting - placeholder description!"
            )
            self.defence = Skills.Skill(
                "Defence", 0, "Defence - placeholder description!"
            )
            self.farming = Skills.Skill(
                "Farming", 0, "Farming - placeholder description!"
            )
            self.firemaking = Skills.Skill(
                "Firemaking", 0, "Firemaking - placeholder description!"
            )
            self.fishing = Skills.Skill(
                "Fishing", 0, "Fishing - placeholder description!"
            )
            self.fletching = Skills.Skill(
                "Fletching", 0, "Fletching - placeholder description!"
            )
            self.herblore = Skills.Skill(
                "Herblore", 0, "Herblore - placeholder description!"
            )
            self.hitpoints = Skills.Skill(
                "Hitpoints", 0, "Hitpoints - placeholder description!"
            )
            self.hunter = Skills.Skill("Hunter", 0, "Hunter - placeholder description!")
            self.magic = Skills.Skill("Magic", 0, "Magic - placeholder description!")
            self.mining = Skills.Skill("Mining", 0, "Mining - placeholder description!")
            self.prayer = Skills.Skill("Prayer", 0, "Prayer - placeholder description!")
            self.ranged = Skills.Skill("Ranged", 0, "Ranged - placeholder description!")
            self.runecraft = Skills.Skill(
                "Runecraft", 0, "Runecraft - placeholder description!"
            )
            self.slayer = Skills.Skill("Slayer", 0, "Slayer - placeholder description!")
            self.smithing = Skills.Skill(
                "Smithing", 0, "Smithing - placeholder description!"
            )
            self.strength = Skills.Skill(
                "Strength", 0, "Strength - placeholder description!"
            )
            self.thieving = Skills.Skill(
                "Thieving", 0, "Thieving - placeholder description!"
            )
            self.woodcutting = Skills.Skill(
                "Woodcutting", 0, "Woodcutting - placeholder description!"
            )
            # If a SkillSet descriptor is provided:
            if descriptor is not None:
                # For each possible skill name:
                for skill_name in Skills.Constants.Container.SKILL_NAMES:
                    skill_name = skill_name.lower()
                    try:
                        # Try to look up the skill XP from the descriptor dictionary
                        skill_xp = descriptor[skill_name]
                    except KeyError:
                        # The skill is not in the descriptor.
                        # If the skill is Hitpoints, then XP must be at least 174 (Level 3).
                        # Otherwise, the XP is set to 0 (Level 1).
                        if skill_name == Skills.Constants.String.HITPOINTS:
                            skill_xp = Skills.Constants.Container.LEVEL_XP[3]
                        else:
                            skill_xp = Skills.Constants.Container.LEVEL_XP[1]

                    # Set the Skill's XP - has side effect of updating Skill.level
                    self.__getattribute__(skill_name).set_xp(skill_xp)

        def __repr__(self):
            descriptor_string = ""
            for skill_name in Skills.Constants.Container.SKILL_NAMES:
                descriptor_string += f'"{skill_name.lower()}": {self.__getattribute__(skill_name.lower()).xp}, '
            descriptor_string = descriptor_string[:-2]
            return f"SkillSet(descriptor=dict({descriptor_string}))"


class Actor(GameType):
    """Base class used for representations of player and non-player entities. Actors have a SkillSet in addition to
    GameType attributes."""

    def __init__(
        self,
        name: str,
        description: str,
        skills: dict[str, int] | Skills.SkillSet,
        pronoun: None | Literal["he", "she", "they"] = "they",
        type_name: None | str = None,
        type_description: None | str = None,
        indefinite_article: None | Literal["a", "an"] = None,
    ):
        assert isinstance(name, str)
        assert isinstance(description, str)
        assert isinstance(skills, dict) or isinstance(skills, Skills.SkillSet)
        assert (pronoun is None) or isinstance(pronoun, str)

        if isinstance(skills, Skills.SkillSet):
            self.skills = skills
        else:
            self.skills = Skills.SkillSet(skills)
        self.name = name
        self.description = description
        self.pronoun = "they" or pronoun
        assert pronoun in ("he", "she", "they")

        super().__init__(
            type_name or self.__class__.__name__,
            type_description or "A player or non-player entity.",
            indefinite_article,
        )


class Player(Actor):
    """A player character."""

    def __init__(
        self,
        name,
        skills: None | dict[str, int] = None,
        pronoun: Literal["he", "she", "they"] = "they",
    ):
        self.skills = Skills.SkillSet(skills)
        self.name = name
        self.pronoun = pronoun
        if self.pronoun == "they":
            self.description = f"{self.pronoun.capitalize()} are level PLACEHOLDER."
        if self.pronoun == "he" or self.pronoun == "she":
            self.description = f"{self.pronoun.capitalize()} is level PLACEHOLDER."
        self.type_name = self.__class__.__name__
        self.type_description = "This is a character controlled by a player."

        super().__init__(
            self.name,
            self.description,
            self.skills,
            self.pronoun,
            self.type_name,
            self.type_description,
            "a",
        )

    def __str__(self):
        return f"A player named {self.name}. {self.description}"

    def __repr__(self):
        return f'Player(name="{self.name}", skills={repr(self.skills)}, pronoun="{self.pronoun}")'


class NonPlayer(Actor):
    pass


if __name__ == "__main__":
    name = "Player"
    ply = Player(name)

    it = 0
    while True:
        ply = Player(name,
            {
                k.lower(): Skills.Constants.Container.LEVEL_XP[
                    random.randint(
                        Skills.Constants.Numeric.MIN_LEVEL,
                        Skills.Constants.Numeric.MAX_LEVEL,
                    )
                ]
                for k in Skills.Constants.Container.SKILL_NAMES
            },
            "he",
        )
        print(it, ply, repr(ply), sep="\n")
        it += 1
        time.sleep(2)
