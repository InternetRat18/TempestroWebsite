"""
© 2025 Internetrat18. All Rights Reserved.

This code is provided publicly for educational viewing and reference only.
You may not copy, redistribute, modify, or use any part of this code for any purpose
without explicit written permission from the author.

Order of functions+/commands:
>Bot initalisation
>Functions: Reading Data (character, attacks, spells)
>Function: WritingData (character data)
>/Cast
>/Attack
>/Action
>/Create_character
>/Remove_Character
>/Reset
>/Create_encounter
>Function Encounter (Turn order, action tracking, condition ticking, etc)
>/Apply
>/Remove
>/Roll
>/Roll_ability
>Function Ability_check 
>Function Roll_dice
>Function Remove_logic (conditions)
>Function updateAutoComplteLists
>Function Calc_damage
>Function Apply_effects (damage, death saves, etc)
>Fucntion Apply_condition_effects (+2AC, -10Speed, etc)
"""
import discord
from discord.ext import commands
from discord import app_commands
from discord import Interaction, ButtonStyle
from discord.ui import Button, View
import random
import time
import math
import sqlite3

intents = discord.Intents.default()
intents.members = True
intents.messages = True #only used for DMs
intents.message_content = True #only used for DMs

#Declare global variables
#Below lists will be defined on bot launch and writing of files, to give autocomplete functionality to core commands.
setOfAllAttacks = {}
setOfAllCharacters = {}
setOfAllSpells = {}

# Define the bot with slash command support
class DnDBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="=", case_insensitive=True, intents=intents)

    async def setup_hook(self):
        #Register the slash commands globally or use guild-specific for faster testing (change using boolean below)
        devTesting = False
        if devTesting:
            print("Running in debug mode. Syncing to test guild.")
            devGuildID = 757478928653877309
            devGuild = discord.Object(id=devGuildID)
            synced = await self.tree.sync(guild=devGuild)
            print("Slash commands synced: " + str(len(synced)))
        else:
            print("Running in production mode. Syncing globally.")
            synced = await self.tree.sync()
            print("Slash commands synced: " + str(len(synced)))
        #Initalise the databse (not not already)
        startTime = time.time()
        DBConnection = sqlite3.connect("Zed\\DNDatabase.db")
        DBCursor = DBConnection.cursor()
        DBCursor.execute("CREATE TABLE IF NOT EXISTS attacks (Name TEXT, Damage TEXT, DamageType TEXT, AttackClass TEXT, Properties TEXT, Conditions TEXT)")
        DBCursor.execute("CREATE TABLE IF NOT EXISTS spells (Name TEXT, SpellLevel TEXT, CastTime TEXT, Damage TEXT, DamageType TEXT, Save TEXT, ExtraLvlDmg TEXT, OnFail TEXT, Conditions TEXT)")
        DBCursor.execute("CREATE TABLE IF NOT EXISTS characters (UserID_FKey INTEGER, Name TEXT, ClassLevel TEXT, Size TEXT, CreatureType TEXT, Race TEXT, Stats TEXT, StatsMod TEXT, HPMaxTempCurrent TEXT, AC TEXT, Speed TEXT, ProfBonus TEXT, Proficiencies TEXT, SavingThrows TEXT, DeathSaves TEXT, VulResImm TEXT, Conditions TEXT, FOREIGN KEY (UserID_FKey) REFERENCES userIDs(UserID_PKey))")
        DBCursor.execute("CREATE TABLE IF NOT EXISTS charactersBK (UserID_FKey INTEGER, Name TEXT, ClassLevel TEXT, Size TEXT, CreatureType TEXT, Race TEXT, Stats TEXT, StatsMod TEXT, HPMaxTempCurrent TEXT, AC TEXT, Speed TEXT, ProfBonus TEXT, Proficiencies TEXT, SavingThrows TEXT, DeathSaves TEXT, VulResImm TEXT, Conditions TEXT, FOREIGN KEY (UserID_FKey) REFERENCES userIDs(UserID_PKey))")
        DBCursor.execute("CREATE TABLE IF NOT EXISTS userIDs (UserID_PKey INTEGER PRIMARY KEY AUTOINCREMENT, UserID TEXT)")
        DBCursor.execute("CREATE TABLE IF NOT EXISTS encounters (GuildID_FKey INTEGER, CharacterOrder TEXT, CharacterOwners TEXT, CurrentIndex INTEGER, ActionsLeft TEXT, FOREIGN KEY (GuildID_FKey) REFERENCES guildIDs(GuildID_PKey))")
        DBCursor.execute("CREATE TABLE IF NOT EXISTS guildIDs (GuildID_PKey INTEGER PRIMARY KEY AUTOINCREMENT, GuildID TEXT)")
        #Upload contents of CSV Files
        DBCursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        Tables = DBCursor.fetchall()
        csvFilesToUpload = ["attacks", "spells"]
        for fileName in csvFilesToUpload:
            with open("Zed\\" + fileName + ".csv", encoding='utf-8') as file: fileLines = file.readlines()
            for line in fileLines:
                row = line.strip().split(",")
                placeholders = ", ".join("?" for _ in row)
                DBCursor.execute("INSERT OR IGNORE INTO "+fileName+" VALUES ("+placeholders+")", row)
        print("["+str(time.time()-startTime)+"]DNDatabase Initalised from CSV Files.")
        DBConnection.commit()
        DBConnection.close()
        #Update autocomplete lists
        updateAutocompleteLists()

# Create the bot instance
client = DnDBot()

# Event: Bot is ready
@client.event
async def on_ready():
    print("Bot is online as " + str(client.user))
    await client.change_presence(activity=discord.Game(name="DND probably"))

#Functions to read info from files. Each Returns [releventDict, Found?(Bool)]
def getCharacterInfo(interaction: discord.Interaction, character: str, BKFile: bool = False) -> tuple[dict, bool]:
    characterDict = {}
    #Query the database for that character (QueryResult)
    DBConnection = sqlite3.connect("Zed\\DNDatabase.db")
    DBCursor = DBConnection.cursor()
    GuildUserIDs = [str(user.id) for user in interaction.guild.members]
    QuestionMarks = ",".join("?" * len(GuildUserIDs))
    Query = "SELECT * FROM characters WHERE LOWER(Name) = LOWER(?)"
    DBCursor.execute(Query, (character,))
    QueryGeneralResult = DBCursor.fetchone()
    Query = "SELECT * FROM characters JOIN userIDs ON characters.UserID_FKey = userIDs.UserID_PKey WHERE userIDs.UserID IN ("+QuestionMarks+") AND LOWER(Name) = LOWER(?)"
    DBCursor.execute(Query, GuildUserIDs + [character])
    QueryResult = DBCursor.fetchone()
    DBConnection.close()
    #Convert the QueryResult into the characterDict
    if QueryGeneralResult and not QueryResult: print("getCharacterInfo Info: Character can not be accessed, owner not in guild.")
    if QueryResult is None: return({}, False)
    QueryResult = [str(Value).lower().strip() for Value in QueryResult]
    characterDict = {"name": str(QueryResult[1]),
                     "class": str(QueryResult[2].split(" ")[0]),
                     "level": float(QueryResult[2].split(" ")[1]),
                     "size": str(QueryResult[3]),
                     "creatureType": str(QueryResult[4]),
                     "race": str(QueryResult[5]),
                     "stats": [int(mod) for mod in str(QueryResult[6]).split("|")[:6]],
                     "statMods": [int(mod) for mod in str(QueryResult[7]).split("|")[:6]],
                     "HPMax": int(str(QueryResult[8]).split("|")[0]),
                     "HPTemp": int(str(QueryResult[8]).split("|")[1]),
                     "HPCurrent": int(str(QueryResult[8]).split("|")[2]),
                     "AC": int(QueryResult[9]),
                     "speed": int(QueryResult[10]),
                     "profBonus": int(QueryResult[11]),
                     "proficiencies": str(QueryResult[12]+ "|").split("|")[:-1],
                     "savingThrows": str(QueryResult[13] + "|").split("|")[:-1][:6],
                     "deathSaves": str(QueryResult[14]),
                     "vulnerabilities": str(QueryResult[15]).split("|")[0].split(" ")[:20],
                     "resistances": str(QueryResult[15]).split("|")[1].split(" ")[:20],
                     "immunities": str(QueryResult[15]).split("|")[2].split(" ")[:20],
                     "conditions": str(QueryResult[16]).split(" ")}
    return(characterDict, True)

def getAttackInfo(attack: str) -> tuple[dict, bool]:
    attackDict = {}
    #Query the database for that attack (QueryResult)
    DBConnection = sqlite3.connect("Zed\\DNDatabase.db")
    DBCursor = DBConnection.cursor()
    Query = "SELECT * FROM attacks WHERE LOWER(Name) = LOWER(?)"
    DBCursor.execute(Query, (attack,))
    QueryResult = DBCursor.fetchone()
    DBConnection.close()
    #Convert the QueryResult into the attackDict
    if QueryResult is None: return({}, False)
    QueryResult = [str(Value).lower().strip() for Value in QueryResult]
    attackDict = {"name": str(QueryResult[0]),
                  "damageDice": str(QueryResult[1] + "+").split("+")[:-1][:5],
                  "damageType": str(QueryResult[2] + "|").split("|")[:-1][:5],
                  "class": str(QueryResult[3]),
                  "properties": str(QueryResult[4] + " ").split(" ")[:-1][:5],
                  "conditions": str(QueryResult[5] + " ").split(" ")[:-1][:5]}
    return(attackDict, True)

def getSpellInfo(spell: str) -> tuple[dict, bool]:
    spellDict = {}
    #Query the database for that spell (QueryResult)
    DBConnection = sqlite3.connect("Zed\\DNDatabase.db")
    DBCursor = DBConnection.cursor()
    Query = "SELECT * FROM spells WHERE LOWER(Name) = LOWER(?)"
    DBCursor.execute(Query, (spell,))
    QueryResult = DBCursor.fetchone()
    DBConnection.close()
    #Convert the QueryResult into the spellDict
    if QueryResult is None: return({}, False)
    QueryResult = [str(Value).lower().strip() for Value in QueryResult]
    spellDict = {"name": str(QueryResult[0]),
                 "level": int(QueryResult[1]),
                 "castTime": str(QueryResult[2]),
                 "damageDice": str(QueryResult[3] + "+").split("+")[:-1][:5],
                 "damageType": str(QueryResult[4] + "/").split("/")[:-1][:5],
                 "save": str(QueryResult[5]),
                 "upcastDamage": str(QueryResult[6]),
                 "onFail": str(QueryResult[7]),
                 "conditions": str(QueryResult[8] + " ").split(" ")[:-1][:10]}
    return(spellDict, True)

def getEncounterInfo(interaction: discord.Interaction) -> tuple[dict, bool]:
    encounterDict = {}
    #Query the database for an encounter linked to the interaction guild id)
    DBConnection = sqlite3.connect("Zed\\DNDatabase.db")
    DBCursor = DBConnection.cursor()
    Query = "SELECT * FROM encounters JOIN guildIDs ON encounters.GuildID_FKey = guildIDs.GuildID_PKey WHERE guildIDs.guildID = (?)"
    DBCursor.execute(Query, (interaction.guild.id,))
    QueryResult = DBCursor.fetchone()
    DBConnection.close()
    if QueryResult is None: return({}, False)
    QueryResult = [str(Value).lower().strip() for Value in QueryResult]
    encounterDict = {"GuildID_FKey": int(QueryResult[0]),
                     "characterOrder": str(QueryResult[1]).split("|"),
                     "characterOwners": str(QueryResult[2]).split("|"),
                     "currentIndex": int(QueryResult[3]),
                     "actionsLeft": [list(map(int, sublist.strip("[]").split(","))) for sublist in QueryResult[4].split("|")]}
    return(encounterDict, True)

def writeEncounterInfo(interaction: discord.Interaction, encounterDict: dict):
    DBConnection = sqlite3.connect("Zed\\DNDatabase.db")
    DBCursor = DBConnection.cursor()
    DBCursor.execute("SELECT * FROM encounters LIMIT 1")
    TableHeaders = [name[0] for name in DBCursor.description]
    TableHeadersFormated = " = ?,".join(TableHeaders)+" = ?"
    Query = "UPDATE encounters SET "+TableHeadersFormated+" WHERE EXISTS (SELECT 1 FROM guildIDs WHERE encounters.GuildID_FKey = guildIDs.GuildID_PKey AND guildIDs.GuildID = ?)"
    DBCursor.execute(Query, (encounterDict["GuildID_FKey"], "|".join(encounterDict["characterOrder"]), "|".join(encounterDict["characterOwners"]), int(encounterDict["currentIndex"]), "|".join(str(sublist) for sublist in encounterDict["actionsLeft"]), interaction.guild.id))
    DBConnection.commit()
    DBConnection.close()
    
#All functions that write to character files call this function.
#Excetions to this include; /Reset
#Others that read database; updateAutocompleteLists()
def writeInfo(tableName: str, infoDict: dict, remove: bool = False, userID: str = 0) -> str:
    #'Sanitise' the inputs
    tableName = tableName.strip().lower()
    #Setup variables
    fields = []
    lines, updatedLines = [], []
    updatedLine, lineName, returnString = "", "", ""
    Query, QueryResult = "", ""
    #Validate data
    if tableName not in ["characters", "charactersbk"]: raise ValueError("writeInfo Error: Invalid file name. File given: " + file)
    #Connect to the database
    DBConnection = sqlite3.connect("Zed\\DNDatabase.db")
    DBCursor = DBConnection.cursor()
    #For characters
    if tableName in ["characters", "charactersbk"]:
        if isinstance(infoDict, dict): #If its a Dict (as it should), convert to list
            fields = [infoDict["name"].title(),
                      infoDict["class"].title() + " " + str(infoDict["level"]),
                      infoDict["size"].title(),
                      infoDict["creatureType"].title(),
                      infoDict["race"].title(),
                      "|".join([str(mod) for mod in infoDict["stats"]]),
                      "|".join([str(mod) for mod in infoDict["statMods"]]),
                      "|".join([str(infoDict["HPMax"]), str(infoDict["HPTemp"]), str(infoDict["HPCurrent"])]),
                      str(infoDict["AC"]),
                      str(infoDict["speed"]),
                      str(infoDict["profBonus"]),
                      "|".join([str(prof).title() for prof in infoDict["proficiencies"]]),
                      "|".join(infoDict["savingThrows"]).upper(),
                      infoDict["deathSaves"],
                      "|".join([" ".join(infoDict["vulnerabilities"]), " ".join(infoDict["resistances"]), " ".join(infoDict["immunities"])]).title(),
                      " ".join(infoDict["conditions"]).title()]
        elif isinstance(infoDict, list): #If its a list (in case of /create_character)
            fields = infoDict
    #Check if character is present
    Query = "SELECT * FROM "+tableName+" WHERE LOWER(Name) = LOWER(?)"
    DBCursor.execute(Query, (fields[0],))
    QueryResult = DBCursor.fetchone()
    #Remove the Dict[Name] from relevent table (If applicable)
    if remove and QueryResult:
        Query = "DELETE FROM "+tableName+" WHERE LOWER(Name) = LOWER(?) AND UserID_FKey IN (SELECT UserID_PKey FROM userIDs WHERE UserID = ?) RETURNING *"
        DBCursor.execute(Query, (fields[0],userID))
        if len(DBCursor.fetchall()) == 0: returnString += "CantRemove"
        Query = "SELECT Name FROM characters JOIN userIDs ON characters.UserID_FKey = userIDs.UserID_PKey WHERE userIDs.UserID = (?) UNION SELECT Name FROM charactersBK JOIN userIDs ON charactersBK.UserID_FKey = userIDs.UserID_PKey WHERE userIDs.UserID = (?)"
        DBCursor.execute(Query, (userID,userID))
        setOfAllReleventCharacters = {row[0] for row in DBCursor.fetchall() if row[0]}
        if len(setOfAllReleventCharacters) == 0: #No characters referenceing that user anymore (in bot characters and charactersBK)
            Query = "DELETE FROM userIDs WHERE UserID = ?"
            DBCursor.execute(Query, (userID,))
    #If Dict[Name] not in relevent table, add it.
    elif QueryResult is None:
        Query = "SELECT * FROM userIDs WHERE UserID = ?"
        DBCursor.execute(Query, (userID,))
        QueryResult = DBCursor.fetchone()
        if QueryResult is None: #userID is NOT in the table, add it
            Query = "INSERT INTO userIDs(UserID) VALUES (?)"
            DBCursor.execute(Query, (userID,))
            Query = "SELECT * FROM userIDs WHERE UserID = ?"
            DBCursor.execute(Query, (userID,))
            QueryResult = DBCursor.fetchone()
        userIDPKey = QueryResult[0]
        QuestionMarks = ", ".join(["?"] * int(len(fields)+1))
        Query = "INSERT INTO "+tableName+" VALUES ("+QuestionMarks+")"
        DBCursor.execute(Query, ([userIDPKey] + fields))
    #Dict[Name] in relevent table, update it
    else:
        DBCursor.execute("SELECT * FROM "+tableName+" LIMIT 1")
        TableHeaders = [name[0] for name in DBCursor.description]
        TableHeadersFormated = " = ?,".join(TableHeaders[2:])+" = ?"
        Query = "UPDATE "+tableName+" SET "+TableHeadersFormated+" WHERE LOWER(Name) = LOWER(?)"
        DBCursor.execute(Query, fields[1:]+fields[:1])
    DBConnection.commit()
    DBConnection.close()
    return(returnString)

#Functions for autocomplete
async def autocomplete_spells(interaction: discord.Interaction, current: str): #Autocomplete for spell
    return [app_commands.Choice(name=spell, value=spell) for spell in setOfAllSpells if current.title() in spell.title()][:25]
async def autocomplete_characters(interaction: discord.Interaction, current: str): #Autocomplete for caster/attacker/roller
    DBConnection = sqlite3.connect("Zed\\DNDatabase.db")
    DBCursor = DBConnection.cursor()
    #setOfAllServerCharacters = setOfAllCharacters
    GuildUserIDs = [str(user.id) for user in interaction.guild.members]
    QuestionMarks = ",".join("?" * len(GuildUserIDs))
    Query = "SELECT Name FROM characters JOIN userIDs ON characters.UserID_FKey = userIDs.UserID_PKey WHERE userIDs.UserID IN ("+QuestionMarks+")"
    DBCursor.execute(Query, GuildUserIDs)
    setOfAllReleventCharacters = {row[0] for row in DBCursor.fetchall()}
    DBConnection.close()
    return [app_commands.Choice(name=caster, value=caster) for caster in setOfAllReleventCharacters if current.title() in caster.title()][:25]
async def autocomplete_attacks(interaction: discord.Interaction, current: str): #Autocomplete for targets (only the first target)
    return [app_commands.Choice(name=attack, value=attack)for attack in setOfAllAttacks if current.title() in attack.title()][:25]

# Slash command: /cast
@client.tree.command(name="cast", description="Cast a spell at a target as a caster.")
@app_commands.describe(spell="The spell to cast (if multible beams write one target for each)",
                       targets="The targets of the spell (seperated by commas)",
                       caster="The one casting the spell",
                       upcast_level="What level you wish to cast this spell (optional)",
                       hit_modifier="Manual to hit mod (or save mod for statDC spells)",
                       damage_modifier="Manual damage mod (only for spells that deal damage)",
                       advantage_override="Used for special circumstances, will override conditional (dis)advantage")
@app_commands.choices(
    advantage_override=[app_commands.Choice(name="Dis-advantage", value="disadvantage"),
                        app_commands.Choice(name="advantage", value="advantage")])
async def cast(interaction: discord.Interaction, spell: str, targets: str, caster: str, upcast_level: int = 0, hit_modifier: int = 0, damage_modifier: int = 0, advantage_override: str = "none"):
    #'Sanatise' the user inputs
    spell = spell.lower().strip()
    targets = targets.lower().strip()
    caster = caster.lower().strip()
    upcast_level = max(0, upcast_level)
    upcast_level = min(9, upcast_level)
    #Setup some variables
    targetDict, casterDict, spellDict = {}, {}, {}
    targetFound, casterFound, spellFound, spellSaved, spellCrit, critImmune = False, False, False, False, False, True
    spellRollToHit, spellAttackBonus, spellSaveDC, damageTotal, spellBonusToHit, spellBonusToDamage = 0, 0, 0, 0, hit_modifier, damage_modifier
    targetDicts, spellDamages, spellDamageTypes, casterConditionsToApply, targetConditionsToApply = [], [], [], [], []
    spellCastingAbility, spellFeedbackString, applyEffectsFeedback, outputMessage, spellHitLine = "", "", "", "", ""
    targetsList = str(targets+",").split(",")[:-1] #List of Strings
    #Get info from the database
    casterDict, casterFound = getCharacterInfo(interaction, caster)
    spellDict, spellFound = getSpellInfo(spell)
    for target in targetsList:
        targetDict, targetFound = getCharacterInfo(interaction, target)
        targetDicts.append(targetDict)
    #Validate Data
        if not targetFound:
            await interaction.response.send_message("The target "+target.title()+" was not found, check input and try again.")
            return()
    if not casterFound:
        await interaction.response.send_message("Caster was not found, check input and try again.")
        return()
    if not spellFound:
        await interaction.response.send_message("Spell was not found, check input and try again.")
        return()
    if spellBonusToDamage > 0 and len(spellDict["damageType"]) == 0:
        await interaction.response.send_message("Having a damage modifier for spells that dont deal damage won't compute. Try again")
        return()
    #Apply upcasting
    if spellDict["level"] <= 0: #Cantrips
        for levRequirement in spellDict["upcastDamage"].split("|"):
            if int(levRequirement) <= casterDict["level"]: spellDict["damageDice"][0] = str(int(spellDict["damageDice"][0][0])+1)+spellDict["damageDice"][0][1:]
    elif upcast_level-spellDict["level"] >= 1: #Add extra damage from upcasting (based on level difference), and repeat the main damage type if there are multiple types
        spellDict["damageDice"].append(str(int(spellDict["upcastDamage"][0])*int(upcast_level-spellDict["level"]))+str(spellDict["upcastDamage"][1:]))
        if len(spellDict["damageType"]) > 1: spellDict["damageType"].append(spellDict["damageType"][0])
    #Derive the caster/spell stats
    abilityMap = {"wizard": "INT", "cleric": "WIS", "druid": "WIS", "ranger": "WIS", "bard": "CHA", "paladin": "CHA", "sorcerer": "CHA", "warlock": "CHA"}
    spellCastingAbility = abilityMap.get(casterDict["class"])
    if spellCastingAbility is None:
        print("cast Error: Spellcasting Ability could not be found for the class: " + casterDict["class"] + ". It has been handled, defulting to INT")
        spellCastingAbility = "INT"
    spellAbilityMod = casterDict["statMods"][["STR", "DEX", "CON", "INT", "WIS", "CHA"].index(spellCastingAbility)]
    spellAttackBonus = casterDict["profBonus"] + spellAbilityMod
    spellSaveDC = 8 + casterDict["profBonus"] + spellAbilityMod
    if spellDict["save"] == "ac": critImmune = False
    #For each target:
    for index, targetDict in enumerate(targetDicts):
        if spellDict["save"] == "ac": spellSaveDC = targetDict["AC"]
        elif spellDict["save"] in ["str", "dex", "con", "int", "wis", "cha"]:
            spellBonusToHit += targetDict["statMods"][["str", "dex", "con", "int", "wis", "cha"].index(spellDict["save"])]
            spellBonusToHit += targetDict["profBonus"] if any(stat in targetDict["savingThrows"] for stat in ["str", "dex", "con", "int", "wis", "cha"]) else 0
        #Roll damage (if relevent)
        spellDamages, spellDamageTypes, spellRollToHit, spellSaved, spellCrit, spellFeedbackString = calc_damage(interaction, casterDict["name"], targetDict["name"], spellDict["damageDice"], spellDict["damageType"], spellBonusToHit, spellBonusToDamage, spellSaveDC, 0, spellDict["onFail"], advantage_override, not critImmune, 0)
        if spellDict["save"] == "ac": spellHitLine = ("❌" if spellSaved else "✅") + " ("+str(spellRollToHit)+"Hit vs "+str(spellSaveDC)+"AC)"
        elif spellDict["save"] in ["str", "dex", "con", "int", "wis", "cha"]: spellHitLine = ("❌" if not spellSaved else "✅") + " ("+str(spellRollToHit)+spellDict["save"].upper()+" vs "+str(spellSaveDC)+"DC)"
        else: spellSaved, spellCrit, spellRollToHit = False, False, 0
        #Apply effects
        damageTotal += sum(spellDamages)
        if not spellSaved: targetConditionsToApply += [condition for condition in spellDict["conditions"] if not condition.startswith("#")]
        if not spellSaved: casterConditionsToApply += [condition for condition in spellDict["conditions"] if condition.startswith("#")]
        applyEffectsFeedback = apply_effects(interaction, targetDict["name"], damageTotal, targetConditionsToApply)
        apply_effects(interaction, casterDict["name"], 0, casterConditionsToApply)
        #Format output string
        outputMessage += "*" + casterDict["name"].title() + "* has casted *" + spellDict["name"].title() + "* targeting *" + targetDict["name"].title() + "*"
        if spellHitLine != "":outputMessage += "\n:dart: Did this spell hit?: " + spellHitLine
        if spellCrit: outputMessage += "\n:tada: This spell attack CRITICAL HIT!"
        if damageTotal >= 1: outputMessage += "\n:crossed_swords: The spell delt: **" + str(damageTotal) + "Dmg** (" + " + ".join(str(spellDamages[i]) + str(spellDamageTypes[i]).title() for i in range(len(spellDamages))) + ")"
        outputMessage += "\n\n"
        #'Reset' Varaibles in here
        damageTotal = 0
        spellBonusToHit = hit_modifier
    #Return string and take away relevent action.
    await interaction.response.send_message(outputMessage)
    await encounter(interaction, "remove action", spellDict["castTime"], casterDict["name"])
cast.autocomplete("spell")(autocomplete_spells)
cast.autocomplete("caster")(autocomplete_characters)
cast.autocomplete("targets")(autocomplete_characters)

# Slash command: /Attack
@client.tree.command(name="attack", description="For all Non-magical attacks")
@app_commands.describe(attacker="The name of character who is attacking",
                       attack="The name of the attack/weapon you want to use",
                       target="The name of character who you want to attack",
                       secondary_attack="follow up attack, usually only used for sneak attacks, superiority dice attacks and duel weilding.",
                       weapon_mod="If your weapon is enchanted with a hit/damage modifier",
                       secondary_weapon_mod="If your secondary weapon is enchanted with a hit/damage modifier",
                       advantage_override="Used for special circumstances, where (dis)advantage is given outside of conditions* (*invisiility included*).")
@app_commands.choices(
    advantage_override=[app_commands.Choice(name="Dis-advantage", value="disadvantage"),
                        app_commands.Choice(name="advantage", value="advantage")])
async def attack(interaction: discord.Interaction, attacker: str, attack: str, target: str, secondary_attack: str = "none", weapon_mod: int = 0, secondary_weapon_mod: int = 0, advantage_override: str = "none"):
    #'Sanitise' the user inputs
    attack = attack.lower().strip()
    secondary_attack = secondary_attack.lower().strip()
    attacker = attacker.lower().strip()
    target = target.lower().strip()
    #Setup some variables.
    outputMessage, extraOutput, applyEffectsFeedback, preferredSkill, attackRollToHitString, secAttackRollToHitString, attackFeedbackString, secAttackFeedbackString, extraEffects, actionsToRemove = "", "", "", "", "", "", "", "", "", ""
    bonusToHit, bonusToDmg, secBonusToHit, secBonusToDmg, attackRollToHit, secAttackRollToHit, damageTotal = 0, 0, 0, 0, 0, 0, 0
    attackDamages, attackDamageTypes, secAttackDamages, secAttackDamageTypes, targetConditionsToApply, attackerConditionsToApply, combinedAttackDamages, combinedAttackDamageTypes = [], [], [], [], [], [], [], []
    attackSaved, attackCrit, secAttackSaved, secAttackCrit = False, False, False, False
    sizeList = ["tiny", "small", "medium", "large", "huge", "gargantuan"]
    #Next, get the relevant information from the attacker, target, and attack files. (This will be rewritten when SQL is integrated.)
    attackerDict, attackerFound = getCharacterInfo(interaction, attacker)
    targetDict, targetFound = getCharacterInfo(interaction, target)
    attackDict, attackFound = getAttackInfo(attack)
    secAttackDict, secAttackFound = getAttackInfo(secondary_attack)
    #If any were not found, tell the user and stop.
    if not attackerFound:
        await interaction.response.send_message("Attacker was not found, check input and try again.")
        return()
    if not targetFound:
        await interaction.response.send_message("Target was not found, check input and try again.")
        return()
    if not attackFound:
        await interaction.response.send_message("Attack was not found, check input and try again.")
        return()
    if secondary_attack != "none" and not secAttackFound:
        await interaction.response.send_message("Secondary attack was not found, check input and try again.")
        return()
    #Ensure read data is valid, this is not rigorous.
    if len(attackDict["damageType"]) > 1 and len(attackDict["damageDice"]) !=  len(attackDict["damageType"]):
        await interaction.response.send_message("The main attack has invalid damage:type ratio.")
        return()
    if "grappling" in attackerDict["conditions"] and (attackFound or secAttackFound):
        await interaction.response.send_message("Attacking while grappling a creature is not allowed. You may use /remove to stop grappling")
        return()
    if secondary_attack != "none":
        if len(secAttackDict["damageType"]) > 1 and len(secAttackDict["damageDice"]) !=  len(secAttackDict["damageType"]):
            await interaction.response.send_message("The off-hand attack has invalid damage format.")
            return()
        if ("light" not in secAttackDict["properties"] or "light" not in attackDict["properties"]) and "special" not in secAttackDict["properties"] and not (attackDict["name"] == secAttackDict["name"] and "versatile" in str(attackDict["properties"])):
            await interaction.response.send_message("That duel-weilding request was not valid.")
            return()
    if attackDict["name"] == "grapple":
        if sizeList.index(targetDict["size"]) > sizeList.index(attackerDict["size"])+1:
            await interaction.response.send_message("The targets size is too large for you to grapple.")
            return()
    if attackDict["name"] == "net":
        if targetDict["size"] in ["huge", "gargantuan"]:
            await interaction.response.send_message("The target is too large to be affected by a net.")
            return()
    #Apply versatile property (if applicable):
    if secAttackFound:
        if attackDict["name"] == secAttackDict["name"] and "versatile" in str(attackDict["properties"]):
            for wepProperty in attackDict["properties"]:
                if wepProperty.startswith("versatile"):
                    secondary_attack, secAttackFound = "none", False
                    attackDict["damageDice"][0] = wepProperty[9:]
    #Now deduce the bonusToHit
    bonusToHit = weapon_mod
    if "finesse" in attackDict["properties"]: bonusToHit += max(attackerDict["statMods"][0], attackerDict["statMods"][1])
    elif attackDict["class"][1:2] == "r": bonusToHit += attackerDict["statMods"][1]
    else: bonusToHit += attackerDict["statMods"][0]
    bonusToDmg = bonusToHit
    if attackDict["class"] in attackerDict["proficiencies"] or attackDict["name"] in attackerDict["proficiencies"]: bonusToHit += attackerDict["profBonus"]
    if secAttackFound: #Similar code for secAttack:
        secBonusToHit = secondary_weapon_mod
        if "finesse" in secAttackDict["properties"]: secBonusToHit += max(attackerDict["statMods"][0], attackerDict["statMods"][1])
        elif secAttackDict["class"][1:2] == "r": secBonusToHit += attackerDict["statMods"][1]
        else: secBonusToHit += attackerDict["statMods"][0]
        secBonusToDmg = secBonusToHit
        if secAttackDict["class"] in attackerDict["proficiencies"] or secAttackDict["name"] in attackerDict["proficiencies"]: secBonusToHit += attackerDict["profBonus"]
    for condition in attackerDict["conditions"]:
        if condition.startswith("bless"):
            bonusToHit += roll_dice(1, 4, 0)
            attackerDict = remove_logic(interaction, attackerDict["name"], "bless")
        if "hunters|mark" in condition:
            bonusToDmg, secBonusToDmg = bonusToDmg + roll_dice(1, 6), secBonusToDmg + roll_dice(1, 6)
            extraOutput += "\n:book: Special effect 'Hunters Mark' triggered! (+1d6 to attack(s) damage)"
    #Roll damage (for normal attacks)
    if "special" not in attackDict["properties"]:
        attackDamages, attackDamageTypes, attackRollToHit, attackSaved, attackCrit, attackFeedbackString = calc_damage(interaction, attackerDict["name"], targetDict["name"], attackDict["damageDice"], attackDict["damageType"], bonusToHit, bonusToDmg, targetDict["AC"], 0, "miss", advantage_override)
        attackRollToHitString, attackTargetDCString, actionsToRemove = str(attackRollToHit) + "Hit", str(targetDict["AC"]) + "AC", actionsToRemove+"Action"
    if secAttackFound:
        if "special" not in secAttackDict["properties"]:
            if secAttackFound: secAttackDamages, secAttackDamageTypes, secAttackRollToHit, secAttackSaved, secAttackCrit, secAttackFeedbackString = calc_damage(interaction, attackerDict["name"], targetDict["name"], secAttackDict["damageDice"], secAttackDict["damageType"], secBonusToHit, secBonusToDmg, targetDict["AC"], 0, "miss", advantage_override)
            if secAttackFound: secAttackRollToHitString, secAttackTargetDCString, actionsToRemove = str(secAttackRollToHit) + "Hit", str(targetDict["AC"]) + "AC", actionsToRemove+"Bonusaction"
    #Roll damage (for special attacks)
    if attackDict["name"] == "net":
        attackRollToHit, extraEffects = ability_check(interaction, attackerDict["name"], "DEX", "none")
        if 8+bonusToDmg < attackRollToHit: attackSaved = True
        attackRollToHitString, attackTargetDCString, actionsToRemove = str(8+bonusToDmg) + "Dex", str(attackRollToHit) + "Dex", actionsToRemove+"Action"
    elif attackDict["name"] == "grapple": 
        if ability_check(interaction, targetDict["name"], "STR", "athletics", "none", True) >= ability_check(interaction, targetDict["name"], "DEX", "acrobatics", "none", True): #Determine if the target is better at Athletics or Acrobatics
            (attackRollToHit, extraEffects), (secAttackRollToHit, _), preferredSkill = ability_check(interaction, attackerDict["name"], "STR", "athletics"), ability_check(interaction, targetDict["name"], "STR", "athletics"), "Athletics"
        else: (attackRollToHit, extraEffects), (secAttackRollToHit, _), preferredSkill = ability_check(interaction, attackerDict["name"], "STR", "athletics"), ability_check(interaction, targetDict["name"], "DEX", "acrobatics"), "Acrobatics"
        attackSaved = False if attackRollToHit >= secAttackRollToHit else True
        attackRollToHitString, attackTargetDCString, actionsToRemove = str(attackRollToHit) + "Athletics", str(secAttackRollToHit) + preferredSkill, actionsToRemove+"Action"
    if secAttackFound:
        if secAttackDict["name"] == "sneak attack":
            secAttackDamages, secAttackDamageTypes, _, _, _, secAttackFeedbackString = calc_damage(interaction, attackerDict["name"], targetDict["name"], [str(int((attackerDict["level"]+1)/2))+"d6"], attackDict["damageType"], 0, 0, targetDict["AC"], 0, "miss", "none", True, attackRollToHit)
            attackDamages, attackDamageTypes = attackDamages+secAttackDamages, attackDamageTypes+secAttackDamageTypes
            secAttackFound = False
    #Apply effects
    combinedAttackDamages, combinedAttackDamageTypes = attackDamages+secAttackDamages, attackDamageTypes+secAttackDamageTypes
    damageTotal += sum(combinedAttackDamages)
    if not attackSaved: targetConditionsToApply += attackDict["conditions"]
    if secAttackFound: targetConditionsToApply += secAttackDict["conditions"]
    applyEffectsFeedback = apply_effects(interaction, target, damageTotal, targetConditionsToApply)
    apply_effects(interaction, attacker, 0, attackerConditionsToApply)
    #Format output
    outputMessage += "*" + attackerDict["name"].title() + "* used *" + attackDict["name"].title() + "* targeting *" + targetDict["name"].title() + "*"
    outputMessage += "\n:dart: Did the main attack hit?: " + ("❌" if attackSaved else "✅") + " (" + attackRollToHitString + " vs " + attackTargetDCString + ")"
    if attackCrit: outputMessage += "\n:tada: Your main attack CRITICAL HIT!"
    if secAttackFound: outputMessage += "\n:dart: Did the off-hand attack hit?: " + ("❌" if secAttackSaved else "✅") + " (" + str(secAttackRollToHit) + "Hit vs " + str(targetDict["AC"]) + "AC)"
    if secAttackFound and secAttackCrit: outputMessage += "\n:tada: Your off-hand attack CRITICAL HIT!"
    if damageTotal >= 1: outputMessage += "\n:crossed_swords: The attacks delt: **" + str(damageTotal) + "Dmg** (" + " + ".join(str(combinedAttackDamages[i]) + str(combinedAttackDamageTypes[i]).title() for i in range(len(combinedAttackDamages))) + ")"
    if "bless" in extraEffects: outputMessage += "\n:book: Special effect 'Bless' triggered! (+1d4 to attack roll/save)"
    if advantage_override != "none": outputMessage += "\n:warning: Manual " + advantage_override.title() + " was given."
    elif "Advantage" in attackFeedbackString: outputMessage += ":grey_exclamation: You were given Advantage."
    elif "Disadvantage" in attackFeedbackString: outputMessage += ":grey_exclamation: You were given Disadvantage."
    if "TargetZeroHP" in applyEffectsFeedback: outputMessage += "\n:skull: " + targetDict["name"].title() + " has reached 0HP."
    #Return string and take away relevent action.
    await interaction.response.send_message(outputMessage)
    if "Action" in actionsToRemove: await encounter(interaction, "remove action", "action", attackerDict["name"])
    if "Bonusaction" in actionsToRemove: await encounter(interaction, "remove action", "bonus action", attackerDict["name"])
attack.autocomplete("attacker")(autocomplete_characters)
attack.autocomplete("attack")(autocomplete_attacks)
attack.autocomplete("target")(autocomplete_characters)
attack.autocomplete("secondary_attack")(autocomplete_attacks)

# Slash command: /Action, hardcode each action allowed
@client.tree.command(name="action", description="For actions other than attacks during combat.")
@app_commands.describe(character="The 'actionee' doing the acting.", action="The Action you want to perform.", target="Some actions require a target e.g. help or sometimes hide.")
@app_commands.choices(action=[app_commands.Choice(name=action, value=action) for action in ["Hide", "Help", "Dodge"][:25]])
async def action(interaction: discord.Interaction, character: str, action: str, target: str = ""):
    #'Sanatise' user inputs
    character = character.strip().lower()
    action = action.strip().lower()
    target = target.strip().lower()
    #Setup some varaibles
    characterDict, targetDict = {}, {}
    characterFound, targetFound, saved = False, False, False
    abilityCheck, abilityContestCheck = 0, 0
    #Get characterInfo
    characterDict, characterFound = getCharacterInfo(interaction, character)
    targetDict, targetFound = getCharacterInfo(interaction, target)
    #Validate Data
    if action == "hide" and "hidden" in str(characterDict["conditions"]):
        await interaction.response.send_message(":exclamation: " + character + " you are already hidden, you can't hide again.")
        return()
    if action == "dodge" and "dodging" in str(characterDict["conditions"]):
        await interaction.response.send_message(":exclamation: " + character + " you are already dodging, you can't dodge again.")
        return()
    if action == "help" and target == "":
        await interaction.response.send_message(":exclamation: Please specify the 'target' you want to help.")
        return()
    if action == "help" and not targetFound:
        await interaction.response.send_message("Target was not found, check input and try again.")
        return()
    #Action help
    if action == "help":
        apply_effects(interaction, target, 0, ["Helped.1"])
        await encounter(interaction, "remove action", "action", character)
        await interaction.response.send_message(target.title() + " is being helped this round.")
    #Action Hide
    elif action == "hide": #Make a stealth check and contest it with a passive perception on the target (if any)
        if targetFound:
            if ability_check(interaction, characterDict["name"], "DEX", "Stealth") < ability_check(interaction, targetDict["name"], "WIS", "Perception", "None", True): saved = True
        if not saved: apply_effects(interaction, character, 0, ["Hidden"])
        await interaction.response.send_message(character.title() + ", you think you are hidden. " + ("✅ (You actually are)" if not saved else "❌ (You are NOT)"))
    #Action Dodge
    elif action == "dodge":
        apply_effects(interaction, target, 0, ["Dodging.1"])
        await encounter(interaction, "remove action", "action", character)
        await interaction.response.send_message(character.title() + ", you focus your effort on dodging until the start of your next turn.")
action.autocomplete("character")(autocomplete_characters)

# Create character via DM (Direct Messages) structured conversation
@client.tree.command(name="create_character", description="Create a character step-by-step for the encounter tracker.")
async def create_character(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Check your DMs to begin character creation.", ephemeral=True) #Sends an immediate message
    user = interaction.user
    dmChannel = await user.create_dm()
    def check(m): #This filters messages so it must be from the inital user and in Tempestros DM's
        return m.author == user and m.channel == dmChannel 
    
    try:
        #Name
        await dmChannel.send("What is your character's **Name**?")
        msgName = await client.wait_for('message', check=check, timeout=300)
        name = msgName.content.strip()
        #Check if name is valid (user doesnt already own a caracter with that name)
        DBConnection = sqlite3.connect("Zed\\DNDatabase.db")
        DBCursor = DBConnection.cursor()
        Query = "SELECT * FROM characters JOIN userIDs ON characters.UserID_FKey = userIDs.UserID_PKey WHERE userIDs.UserID = ? AND LOWER(Name) = LOWER(?)"
        DBCursor.execute(Query, (user.id, name))
        QueryResult = DBCursor.fetchone()
        if QueryResult: #Character found from that user(id) w/ name
            await dmChannel.send("You already own a character with that name (Character creation cancelled).\nTry again with a unique name or use /remove_character to remove the character.")
            return()
        DBConnection.close()
        #Class and Level
        await dmChannel.send("What is your **Class and Level**? (e.g., Wizard 9)\nFor GM's, if this is a monster, enter 'Monster' + CR.")
        msgClassAndLevel = await client.wait_for('message', check=check, timeout=300)
        ClassLevel = msgClassAndLevel.content.strip()
        #Size
        sizeList = ["Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"]
        sizePrompt = "\n".join([str(i+1)+". "+size for i, size in enumerate(sizeList)])
        await dmChannel.send("What is your characters **Size**? Usually this is 'Medium'.\nReply with the number that represents your characters size (e.g. 3).\n"+sizePrompt)
        msgSize = await client.wait_for('message', check=check, timeout=300)
        size = msgSize.content.strip()
        if int(size)-1 < 0 or int(size)-1 > 5:
            await dmChannel.send("❌ Incorrect entry. Please start over.")
            return()
        size = sizeList[int(size)-1]
        #CreatureType
        await dmChannel.send("What is your characters **Creature Type**? Usually this is 'Humanoid'.")
        msgCreatureType = await client.wait_for('message', check=check, timeout=300)
        creatureType = msgCreatureType.content.strip()
        #Race
        await dmChannel.send("What is your characters **Race**? (E.g. 'Human'.)\nFor GM's, if your monster doesnt have a race, enter 'None'")
        msgRace = await client.wait_for('message', check=check, timeout=300)
        race = msgRace.content.strip()
        #Stats
        await dmChannel.send("Enter your **Stats** in STR,DEX,CON,INT,WIS,CHA order separated by commas (e.g. 10,15,14,12,13,8).")
        msgStats = await client.wait_for('message', check=check, timeout=300)
        rawStats = msgStats.content.strip().replace(",", "|")
        statsList = rawStats.split("|")
        if len(statsList) != 6:
            await dmChannel.send("❌ Incorrect format. Please start over.")
            return()
        modsList = [str((int(stat) - 10) // 2) for stat in statsList]
        statMods = "|".join(modsList)
        #HP
        await dmChannel.send("What is your **Max HP**?")
        msgHp = await client.wait_for('message', check=check, timeout=300)
        maxHp = msgHp.content.strip()
        #AC
        await dmChannel.send("What is your **Armor Class (AC)**, including bonuses?")
        msgAc = await client.wait_for('message', check=check, timeout=300)
        Ac = msgAc.content.strip()
        #Speed
        await dmChannel.send("What is your **Speed** (in ft)?")
        msgSpeed = await client.wait_for('message', check=check, timeout=300)
        speed = msgSpeed.content.strip()
        #Calculate proficiency bonus
        try:
            level = int(ClassLevel.split()[-1])
            if level >= 17: profBonus = 6
            elif level >= 13: profBonus = 5
            elif level >= 9: profBonus = 4
            elif level >= 5: profBonus = 3
            else: profBonus = 2
        except:
            profBonus = 2
        #Skill Proficiencies
        skillsList = ["Acrobatics", "Animal Handling", "Arcana", "Athletics", "Deception", "History", "Insight", "Intimidation", "Investigation", "Medicine", "Nature", "Perception", "Performance", "Persuasion", "Religion", "Sleight of Hand", "Stealth", "Survival"]
        skillsPrompt = "\n".join([str(i+1)+". "+skill for i, skill in enumerate(skillsList)])
        await dmChannel.send("Select your **Skill Proficiencies** by replying with numbers separated by commas.\nFor expertise, add 'E' afterwards (e.g. 3,6,12E).\nIf you have no skills, enter '0'.\n"+skillsPrompt)
        msgProficiencies = await client.wait_for('message', check=check, timeout=300)
        entries = [x.strip().upper() for x in msgProficiencies.content.strip().split(',')]
        profSelected = []
        for entry in entries:
            expertise = entry.upper().endswith("E")
            num_part = entry[:-2] if expertise else entry
            if num_part.isdigit():
                idx = int(num_part) - 1
                if 0 <= idx < len(skillsList):
                    skill = skillsList[idx]
                    if expertise: skill += "X2"
                    profSelected.append(skill)
        skillProficiencies = "|".join(profSelected)
        #Weapon Proficiencies
        await dmChannel.send("Select your **Weapon Proficiencies** by replying with numbers separated by commas. Add individual weapons at the end using their name as in the Players Handbook.\nIf you have no weapon proficiencies, enter 'None'.\n1. Simple Melee\n2. Simple Ranged\n3. Martial Melee\n4. Martial Ranged\nExample: 1,2,Rapier,Heavy crossbow")
        msgWeapons = await client.wait_for('message', check=check, timeout=300)
        weaponProficiencies = msgWeapons.content.strip()
        weaponProficiencies = weaponProficiencies.replace("1", "SM")
        weaponProficiencies = weaponProficiencies.replace("2", "SR")
        weaponProficiencies = weaponProficiencies.replace("3", "MM")
        weaponProficiencies = weaponProficiencies.replace("4", "MR")
        weaponProficiencies = weaponProficiencies.split(",")
        proficiencies = "|".join([skillProficiencies] + weaponProficiencies)
        if proficiencies.startswith("|"): proficiencies = proficiencies[1:]
        #Saving Throws
        await dmChannel.send("List your **saving throws you are proficient in**, separated by commas (e.g. CON,WIS).\n If you have no saving throws, enter 'None'.")
        msgSaved = await client.wait_for('message', check=check, timeout=300)
        savingThrows = msgSaved.content.strip()
        savingThrows = savingThrows.replace(",", "|")
        #Vun/Res/Imm
        await dmChannel.send("List your **Vulnerabilities/Resistances/Immunities**, individually separated by spaces and each category separated by '/' (or enter None/None/None).\n E.g. 'Cold Fire/Piercing Slashing Bludgeoning/Crits")
        msgVunResImm = await client.wait_for('message', check=check, timeout=300)
        VunResImm = msgVunResImm.content.strip()
        VunResImm = VunResImm.replace("/", "|")
        #Confirmation preview
        #DEV LINE characterInfoList = name.split(",")
        characterInfoList = [name,ClassLevel,size,creatureType,race,rawStats,statMods,maxHp+"|0|"+maxHp,Ac,speed,profBonus,proficiencies,savingThrows,"0|0",VunResImm,"None"]
        view = ConfirmCancelView()
        await dmChannel.send(":pencil: Here is your generated character line:\n```"+str(characterInfoList)+"```\nIf you are unsure weather this character line is correct, you can run a test attack before your encounter (making sure to /reset afterwards).\nPlease confirm or cancel to complete your character creation:", view=view)
        await view.wait()
        #If confirmed, write it in both files (saves user having to /reset for the character to work).
        if view.value:
            writeInfo("characters", characterInfoList, False, str(user.id))
            writeInfo("charactersBK", characterInfoList, False, str(user.id))
            updateAutocompleteLists()
            await dmChannel.send("✅ "+name+" has been saved successfully! (Its normal for the interaction to fail)")
        else:
            await dmChannel.send("❌ Character creation cancelled.")

    except asyncio.TimeoutError:
        await dmChannel.send(":hourglass: Timeout reached. Please run the command again if you wish to create your character (Any info entered has been voided).")

class ConfirmCancelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.value = None

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        button.disabled = True
        await interaction.message.edit(view=self)
        self.stop()
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        button.disabled = True
        await interaction.message.edit(view=self)
        self.stop()

# Slash command: /Remove_character
@client.tree.command(name="remove_character", description="Remove a character from the database by name.")
@discord.app_commands.describe(character="The name of the character to remove.")
async def remove_character(interaction: discord.Interaction, character: str):
    #'Sanitise' user inputs
    character = character.strip().lower()
    #Setup some varaibles
    characterDict = {}
    characterFound = False
    feedbackString, outputMessage = "", ""
    #Get the relevant information from the character
    characterDict, characterFound = getCharacterInfo(interaction, character)
    #Validate data
    if not characterFound:
        await interaction.response.send_message("Character was not found, check input and try again.")
        return()
    #Remove it from the file (+BK)
    feedbackString += writeInfo("characters", characterDict, True, str(interaction.user.id))
    feedbackString += writeInfo("charactersBK", characterDict, True, str(interaction.user.id))
    #Format and send response
    if "CantRemoveCantRemove" in feedbackString: outputMessage = "Unable to remove another users character."
    else: outputMessage = characterDict["name"].title() + " was removed from the characters database."
    await interaction.response.send_message(outputMessage)
remove_character.autocomplete("character")(autocomplete_characters)

# Slash command: /Reset
@client.tree.command(name="reset", description="This command will reset the character database using the backup.")
async def reset(interaction: discord.Interaction):
    try:
        DBConnection = sqlite3.connect("Zed\\DNDatabase.db")
        DBCursor = DBConnection.cursor()
        DBCursor.execute("SELECT * FROM characters LIMIT 1")
        TableHeaders = [name[0] for name in DBCursor.description]
        TableHeadersFormated = ", ".join(TableHeaders)
        TableBKHeadersFormated = "charactersBK." + ", charactersBK.".join(TableHeaders)
        GuildUserIDs = [str(user.id) for user in interaction.guild.members]
        QuestionMarks = ",".join("?" * len(GuildUserIDs))
        Query = "UPDATE characters SET ("+TableHeadersFormated+") = (SELECT "+TableBKHeadersFormated+" FROM charactersBK WHERE charactersBK.UserID_FKey = characters.UserID_FKey AND charactersBK.Name = characters.Name) WHERE UserID_FKey IN (SELECT userIDs.UserID_PKey FROM userIDs WHERE userIDs.UserID IN ("+QuestionMarks+"))"
        DBCursor.execute(Query, GuildUserIDs)
        DBConnection.commit()
        DBConnection.close()
        await interaction.response.send_message("✅ Character database has been reset to the backup.")
    except Exception as e:
        await interaction.response.send_message("❌ Failed to reset the database: " + e)
    updateAutocompleteLists()

# Slash command: /Create encounter
@client.tree.command(name="create_encounter", description="To create an encounter, usually only used by the DM/GM")
@app_commands.describe(characters="The name of all characters (+monsters) you wish to be in the encounter, in turn order. Separate each character by a comma(,).", character_owners="The name(or @'s) of personnel who are owners of the characters. Have them in the same order as the characters entered.")
async def create_encounter(interaction: discord.Interaction, characters: str, character_owners: str):
    #'Sanitise' the user inputs (and transfer to list type)
    characterList = characters.split(",")
    characterList = [s.lower() for s in characterList]
    characterList = [s.strip() for s in characterList]
    character_owners = character_owners.split(",")
    character_owners = [s.lower() for s in character_owners]
    character_owners = [s.strip() for s in character_owners]
    #Setup some variables
    index = 0
    charcterDict = {}
    characterFound = False
    #Find characters full names (and if they exist)
    for index, character in enumerate(characterList):
        characterDict, characterFound = getCharacterInfo(interaction, character)
        if not characterFound:
            await interaction.response.send_message(character.title() + " could not be found, check input and try again.")
            return()
        characterList[index] = characterDict["name"]
    #Create the encounter
    await interaction.response.send_message("Encounter has started.")
    await encounter(interaction, "start", characterList, character_owners)

#Function for everything related to the encounter
async def encounter(interaction, command: str, info1=None, info2=None):
    #Command start encounter
    if command == "start":
        DBConnection = sqlite3.connect("Zed\\DNDatabase.db")
        DBCursor = DBConnection.cursor()
        Query = "SELECT * FROM guildIDs WHERE GuildID = ?"
        DBCursor.execute(Query, (interaction.guild.id,))
        QueryResult = DBCursor.fetchone()
        #if QueryResult is not None: await interaction.response.send_message("This guild already has an encounter")
        if QueryResult is None: #guildID is NOT in the table, add it
            Query = "INSERT INTO guildIDs(GuildID) VALUES (?)"
            DBCursor.execute(Query, (interaction.guild.id,))
            Query = "SELECT * FROM guildIDs WHERE GuildID = ?"
            DBCursor.execute(Query, (interaction.guild.id,))
            QueryResult = DBCursor.fetchone()
        guildIDPKey = QueryResult[0]
        Query = "INSERT INTO encounters VALUES (?, ?, ?, ?, ?)"
        DBCursor.execute(Query, ([guildIDPKey, "|".join(info1), "|".join(info2), 0, "|".join([str("[1, 1, 1]") for character in info1])]))
        DBConnection.commit()
        DBConnection.close()
        await encounter(interaction, "start turn")
    #Command start turn
    elif command == "start turn":
        #Get info from te counter state & current character + setup some ints
        encounterDict, encounterFound = getEncounterInfo(interaction)
        if not encounterFound: print("encounter 'start turn' Error: Critical error, encounter could not be found. This should not be posible.")
        characterDict, characterFound = getCharacterInfo(interaction, encounterDict["characterOrder"][encounterDict["currentIndex"]])
        if not characterFound: print("encounter 'start turn' Error: Critical error, character could not be found. Attemped to search for: " + str(encounterDict["characterOrder"][encounterDict["currentIndex"]]))
        deathSaveRoll, actCount, bActCount, rActCount, turnsRemaining = 0, 1, 1, 1, 0
        #Initalise the output Message
        outputMessage = (characterDict["name"].title() + " (" + encounterDict["characterOwners"][encounterDict["currentIndex"]] + ") is starting their turn."
                         + "\n:hourglass: " + encounterDict["characterOrder"][(encounterDict["currentIndex"] + 1) % len(encounterDict["characterOrder"])].title()
                         + " (" + encounterDict["characterOwners"][(encounterDict["currentIndex"] + 1) % len(encounterDict["characterOwners"])] + ")" + " has their turn next.")
        #If the character is 0hp, roll deathsaves for their turn
        if characterDict["HPCurrent"] <= 0:
            deathSaveRoll = roll_dice(1, 20)
            if deathSaveRoll >= 10:
                if int(characterDict["deathSaves"].split("|")[0]) >= 2:
                    outputMessage += "\n:star2: Your character has been revived to 1hp "
                    apply_effects(interaction, characterDict["name"], 1, [], [])
                else: outputMessage += "\n:coffin: Your character is at 0hp "
                outputMessage += "(Your death save succeeded :sparkles:)"
                apply_effects(interaction, characterDict["name"], 0, [], ["DeathsaveSuccess"])
            else:
                if int(characterDict["deathSaves"].split("|")[1]) >= 2:
                    del encounterDict["characterOrder"][encounterDict["characterOrder"].index(characterDict["name"])]
                    del encounterDict["characterOwners"][encounterDict["characterOrder"].index(characterDict["name"])]
                    encounterDict["currentIndex"] -= 1
                    outputMessage += "\n:skull: Your character has died and has been removed from the turn order."
                else: outputMessage += "\n:coffin: Your character is at 0hp "
                outputMessage += "(Your death save failed :drop_of_blood:)"
                apply_effects(interaction, characterDict["name"], 0, [], ["DeathsaveFail"])
            await interaction.followup.send(outputMessage)
            await encounter(interaction, "end turn")
            return()
        #If the character isn't a monster, show their HP and tempHP (if applicable)
        if not characterDict["class"].startswith("monster"):
            outputMessage += "\n:heart: Your player character is at " + str(characterDict["HPCurrent"]) + "HP"
            if characterDict["HPTemp"] > 0: outputMessage += " + " + str(characterDict["HPTemp"] + "TempHP")
            outputMessage += "."
        #Check conditions related to actions
        for condition in characterDict["conditions"]:
            if condition.startswith("+Action"): actCount += 1
            elif condition.startswith("-Action"): actCount -= 1
            elif condition.startswith("Noreactions"): rActCount = 0
            elif condition.startswith("Nobonusactions"): bActCount = 0
        #Tick down conditions (if applicable)
            if "." in condition:
                conditionName = str(condition.split(".")[0])
                turnsRemaining = int(condition.split(".")[1])-1
                if turnsRemaining <= 0: characterDict, _ = remove_logic(interaction, characterDict, condition)
                else:
                    characterDict, _ = remove_logic(interaction, characterDict, condition)
                    apply_effects(interaction, characterDict["name"], 0, [conditionName+"."+str(turnsRemaining)])
        #Re-retrive the caracters info, and show their active conditions
        characterDict, characterFound = getCharacterInfo(interaction, encounterDict["characterOrder"][encounterDict["currentIndex"]])
        if not characterFound: print("encounter 'start turn' Error: Character could not be found for the 2nd time. Attemped to search for: " + str(encounterDict["characterOrder"][encounterDict["currentIndex"]]))
        outputMessage += "\n:face_with_spiral_eyes: Your active conditions: " + str(characterDict["conditions"])
        #Update the encounter state with the action count and print the message
        encounterDict["actionsLeft"][encounterDict["currentIndex"]] = [actCount, bActCount, rActCount]
        writeEncounterInfo(interaction, encounterDict)
        outputMessage += "\n:stopwatch: You will have ten(10) minutes to use your actions.\n:notepad_spiral: Check off your actions below as you go to keep track!"
        await interaction.followup.send(outputMessage, view=ActionView(encounterDict))
    #Command end turn
    elif command == "end turn":
        encounterDict, encounterFound = getEncounterInfo(interaction)
        if not encounterFound: print("encounter 'end turn' Error: Critical error, encounter could not be found. This should not be posible.")
        encounterDict["currentIndex"] += 1
        if encounterDict["currentIndex"] >= len(encounterDict["characterOrder"]):
            encounterDict["currentIndex"] = 0
            await interaction.followup.send(":recycle: Going back to the start of the round. Environmental effects happen now.")
        writeEncounterInfo(interaction, encounterDict)
        await encounter(interaction, "start turn")
    #Command remove action
    elif command == "remove action":
        try: #Allows /cast and /attack to be used outside of an encounter
            encounterDict, encounterFound = getEncounterInfo(interaction)
            if not encounterFound: raise ValueError("encounter 'remove action' Error: Encounter could not be found.")
            actionIndex = {"action": 0, "bonus action": 1, "reaction": 2}.get(info1)
            if actionIndex is None: raise ValueError("Invalid value provided for action. Action given: " + str(info1))
            if info2 is None: #If a character is entered
                if encounterDict["actionsLeft"][encounterDict["characterOrder"].index(info2)][actionIndex] <= 0: #If it already is 0, send a follow-up message
                    message = await interaction.original_response()
                    await message.edit(content=message.content + "\n:grey_exclamation: You did not have the required "+info1.title()+" to do that (effects still applied)")
                encounterDict["actionsLeft"][encounterDict["characterOrder"].index(info2)][actionIndex] -= 1
                print("Removed " + info1.title() + " from " + info2.title() + ".")
                writeEncounterInfo(interaction, encounterDict)
            else: #remove it from the current characters turn
                print("No character entered, removing " + info1.title() + " from current indexed character.")
                encounterDict["actionsLeft"][encounterDict["currentIndex"]][actionIndex] = max(encounterDict["actionsLeft"][encounterDict["currentIndex"]][actionIndex]-1, 0)
                writeEncounterInfo(interaction, encounterDict)
                return(encounterDict["actionsLeft"][encounterDict["currentIndex"]][actionIndex])
            #await interaction.response.edit(view=ActionView(encounterDict)) BROKEN: WANTS TO UPDATE ENCOUNTER INTERACTION (the one with buttons), CURRENT INTERACTION OBJECT IS THE ACTION (/attack or /cast)
        except Exception as e: print(str(e) + ". " + info1.title() + " could not be removed, is enounter started?")
        
class ActionView(View):
    def __init__(self, encounterDict):
        super().__init__(timeout=600) #Max timeout time is 15mins (900s)
        self.encounterDict = encounterDict
        for index, item in enumerate(self.children):
            if index != 3:
                if encounterDict["actionsLeft"][encounterDict["currentIndex"]][index] <= 0:
                    item.disabled = True

    async def on_timeout(self):
        #Encounter no longer valid, remove it from database
        DBConnection = sqlite3.connect("Zed\\DNDatabase.db")
        DBCursor = DBConnection.cursor()
        Query = "DELETE FROM encounters WHERE GuildID_FKey = ?"
        DBCursor.execute(Query, (self.encounterDict["GuildID_FKey"],))
        Query = "DELETE FROM guildIDs WHERE GuildID_PKey = ?"
        DBCursor.execute(Query, (self.encounterDict["GuildID_FKey"],))
        DBConnection.commit()
        DBConnection.close()
        
    @discord.ui.button(label="Action", style=ButtonStyle.primary)
    async def action(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("Action button pressed, it has been marked as used.", ephemeral=True)
        if await encounter(interaction, "remove action", "action", "") <= 0: button.disabled = True
        await interaction.message.edit(view=self)
    @discord.ui.button(label="BonusAction", style=ButtonStyle.secondary)
    async def bonus_action(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("Bonus action button pressed, it has been marked as used.", ephemeral=True)
        if await encounter(interaction, "remove action", "bonus action", "") <= 0: button.disabled = True
        await interaction.message.edit(view=self)
    @discord.ui.button(label="Reaction", style=ButtonStyle.success)
    async def reaction(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("Reaction button pressed, it has been marked as used.", ephemeral=True)
        if await encounter(interaction, "remove action", "reaction", "") <= 0: button.disabled = True
        await interaction.message.edit(view=self)
    @discord.ui.button(label="End Turn", style=ButtonStyle.danger)
    async def end_turn(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("You have ended your turn.", ephemeral=True)
        await interaction.message.edit(view=None) #Removes all buttons
        await encounter(interaction, "end turn")

# Slash command: /Apply
@client.tree.command(name="apply", description="Manually apply damage, healing, or conditions to a character (typicly used by DM).")
@app_commands.describe(target="The character you want to apply these effects to.",damage="The damage to apply to the target(0 for nothing, and negative for healing).",condition="Condition you wish to apply to the target",condition_duration="how many turns should the condition last (leave blank for no duration)")
@app_commands.choices(condition=[app_commands.Choice(name=cond, value=cond) for cond in ["Invisible", "Hidden", "Surprised", "Flanking", "Helped", "FaerieFire", "GuidingBolt", "Unaware", "Blinded", "Prone", "Poisoned", "Restrained", "Grappled", "Obscured", "Exhaustion3", "Silenced", "Dodging", "Cursed", "Paralyzed"][:25]])
async def apply(interaction: discord.Interaction, target: str, damage: int, condition: str = "", condition_duration: int = 0):
    #'Sanatise' User inputs
    target = target.strip().lower()
    condition = condition.strip().lower()
    condition_duration = max(0, condition_duration)
    #Setup some variables
    targetDict = {}
    targetFound = False
    returnString, outputMessage = "", ""
    #Get target info
    targetDict, targetFound = getCharacterInfo(interaction, target)
    #Validate Data
    if not targetFound:
        await interaction.response.send_message("The target "+target.title()+" was not found, check input and try again.")
        return()
    if condition == "" and condition_duration > 0:
        await interaction.response.send_message("Condition duration was entered without a condition. This does not compute.")
        return()
    #Apply the effects
    if condition_duration <= 0: returnString = apply_effects(interaction, targetDict["name"], damage, [condition])
    elif condition_duration > 0: returnString = apply_effects(interaction, targetDict["name"], damage, [condition+"."+str(condition_duration)])
    #Format output
    if int(damage) >= 0: outputMessage += ":crossed_swords: " + target.title() + " has taken " + str(damage) + " damage."
    elif int(damage) < 0: outputMessage += ":heart: " + target.title() + " has been healed for " + str(int(damage)*-1) + " damage."
    if condition != "":
        outputMessage += "\n" + str(condition) + " has also been applied"
        if int(condition_duration) > 0: outputMessage += " for " + str(int(condition_duration)) + " rounds"
        outputMessage += "."
    if "TargetZeroHP" in returnString: outputMessage += "\n:skull: " + targetDict["name"] + " has reached 0HP."
    await interaction.response.send_message(outputMessage)
apply.autocomplete("target")(autocomplete_characters)

# Slash command: /Remove
@client.tree.command(name="remove", description="Manually remove a condition from a character (typicly used by DM).")
@app_commands.describe(target="The character you want to remove the condition from.",condition="Condition you wish to remove from the target, give none for a list of conditions on the target.")
async def remove(interaction: discord.Interaction, target: str, condition: str = ""):
    #'Sanitise' inputs
    target = target.strip().lower()
    condition = condition.strip().lower()
    #Declare some variables
    conditionFound = False
    #Get the relevent info from the target
    targetDict, targetFound = getCharacterInfo(interaction, target)
    #Attempt removal of condition
    targetDict, conditionFound = remove_logic(interaction, targetDict, condition)
    if not conditionFound:
        await interaction.response.send_message(target.title() + " did not have '" + condition.title() + "' present as a condition.")
        return()
    await interaction.response.send_message(condition.title() + " has been removed from " + target.title())

# Slash command: /Roll. This is an independent command.
@client.tree.command(name="roll", description="Roll any number of dice!")
@app_commands.describe(dice="the dice you wish to roll, separated by '+'. e.g. 1d20+4d6", modifier="Any positive (or negative) modifier you wish to add. e.g. +12 or -5")
async def roll(interaction: discord.Interaction, dice: str, modifier: int = 0):
    totalResult = int(modifier)
    outputMessage = "Rolling: " + dice 
    if "+" not in dice: diceArguments = 0
    else: diceArguments = len(dice.split("+"))-1
    for i in range(diceArguments+1):
        diceRoll = dice.split("+")[i]
        diceCount = int(diceRoll.split("d")[0])
        diceSides = int(diceRoll.split("d")[1])
        if diceCount == 0 or diceSides == 0: outputMessage += "\n- Nothing, no dice were rolled here. "
        else:
            outputMessage += "\n- " + str(diceSides) + "-sided dice; "
            while diceCount > 0:
                diceResult = random.randint(1, diceSides)
                totalResult += diceResult
                diceCount -= 1
                if diceCount > 0: outputMessage += str(diceResult) + ", "
                elif diceCount == 0: outputMessage += str(diceResult) + ". "
    if modifier != 0: outputMessage += "\n- Modifier: " + str(modifier) + ". "
    await interaction.response.send_message(outputMessage + "\n**Total: " + str(int(totalResult)) + "**")

# Slash command: /Roll_ability
@client.tree.command(name="roll_ability", description="This command will reset the character database using the backup.")
@app_commands.describe(roller="Character that is making the ability check.", ability="The ability you want to check, weather it be a skill or stat.", advantage_override="Give (dis)advantage?", passive="If it should return the average roll. (False by defult)")
@app_commands.choices(
    advantage_override=[app_commands.Choice(name="Dis-advantage", value="disadvantage"),
                        app_commands.Choice(name="advantage", value="advantage")],
    ability=[app_commands.Choice(name=cond, value=cond) for cond in ["STR", "DEX", "CON", "INT", "WIS", "CHA", "Athletics", "Acrobatics", "Sleight of Hand", "Stealth", "Arcana", "History", "Investigation", "Nature", "Religion", "Animal Handling", "Insight", "Medicine", "Perception", "Survival", "Deception", "Intimidation", "Performance", "Persuasion"][:25]])
async def roll_ability(interaction: discord.Interaction, roller: str, ability: str, advantage_override: str = "none", passive: bool = False):
    #'Sanitise' user inputs
    roller = roller.strip().lower()
    ability = ability.strip().lower()
    #Get the relevant information from the roller
    rollerDict, rollerFound = getCharacterInfo(interaction, roller)
    #Setup some variables
    relevantStat, outputMessage = "none", ""
    abilityResult = 0
    if ability not in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
        if ability in ["athletics"]: relevantStat = "STR"
        elif ability in ["acrobatics", "sleight of hand", "stealth"]: relevantStat = "DEX"
        elif ability in ["arcana", "history", "investigation", "nature", "Religion"]: relevantStat = "INT"
        elif ability in ["animal handling", "insight", "medicine", "perception", "survival"]: relevantStat = "WIS"
        elif ability in ["deception", "intimidation", "performance", "persuasion"]: relevantStat = "CHA"
    #Format and send output:
    abilityResult, feedbackString = ability_check(interaction, roller, relevantStat, ability, advantage_override, passive)
    outputMessage = roller.title() + ", your " + ability + " check rolled: " + str(abilityResult) + "."
    if "Bless" in feedbackString: outputMessage += "\n:book: Special effect 'Bless' triggered! (+1d4 to attack roll/save)"
    if "Advantage" in feedbackString: outputMessage += ":grey_exclamation: You were given Advantage."
    if "Disadvantage" in feedbackString: outputMessage += ":grey_exclamation: You were given Disadvantage."
    await interaction.response.send_message(outputMessage)
roll_ability.autocomplete("roller")(autocomplete_characters)

#function to Roll ability checks/saving throws
def ability_check(interaction: discord.Interaction, roller: str, abilityStat: str, abilityCheck: str, advantage_override: str = "none", passive: bool = False) -> tuple[int, str]:
    #'Sanitise' inputs
    roller = roller.strip().lower()
    abilityStat = abilityStat.strip().upper()
    abilityCheck = abilityCheck.strip().lower()
    advantage_override = advantage_override.strip().lower()
    #Get the relevant information from the roller
    rollerDict, rollerFound = getCharacterInfo(interaction, roller)
    #Setup some variables
    advantage, disadvantage = False, False
    extraEffects = ""
    #Dedeuce the modifier
    if abilityStat == "NONE": abilityStat = abilityCheck.upper() #Saving throw, set stat to 'ability'.
    modifier = int(rollerDict["statMods"][["STR","DEX","CON","INT","WIS","CHA"].index(abilityStat)])
    if abilityCheck == "none": #Saving throw
        for profSavingThrow in rollerDict["savingThrows"]:
            if profSavingThrow == abilityStat: modifier += rollerDict["profBonus"] #Proficiency
        for condition in rollerDict["conditions"]:
            if condition.startswith(abilityStat): modifier += int(condition.replace(abilityStat, "")) #e.g. STR+2 condition
            if condition.startswith("bless") and not passive: #Spell specific bonus
                modifier += roll_dice(1, 4) #Consume the bonus
                extraEffects += "Bless"
                remove_logic(interaction, roller, "bless") #Remove the bonus (its consumed)
    else:
        for ability in rollerDict["proficiencies"]:
            if ability == abilityCheck: modifier += rollerDict["profBonus"] #Proficiency
            print("ability_check Info: Attempting Expert; does " + ability + "==" + abilityCheck+"x2")
            if ability == abilityCheck+"x2": modifier += rollerDict["profBonus"] #Expertise
        for condition in rollerDict["conditions"]:
            if condition.startswith(abilityCheck): modifier += int(condition.replace(abilityCheck, "")) #e.g. Stealth+10 (for 'Pass without trace')
    #Deduce (dis)advantage
    for condition in rollerDict["conditions"]:
        advantage = True if condition.startswith("+adv"+abilityCheck+"save") else False
        disadvantage = True if condition.startswith("-adv"+abilityCheck+"save") else False
    advantage = True if advantage_override == "advantage" else False
    disadvantage = True if advantage_override == "advantage" else False
    #Roll the ability and return the result
    abilityRoll = roll_dice(1, 20, modifier)
    if advantage and not disadvantage: abilityRoll, extraEffects = max(abilityRoll, roll_dice(1, 20, modifier)), extraEffects+"Disadvantage"
    if disadvantage and not advantage: abilityRoll, extraEffects = min(abilityRoll, roll_dice(1, 20, modifier)), extraEffects+"Advantage"
    if passive: abilityRoll = 10 + modifier #Take the average roll
    return(abilityRoll, extraEffects)

#function to Roll X-sided dice, Y-times with a Z modifier
def roll_dice(dice_count: int, dice_sides: int, modifier: int = 0) -> int:
    Total = modifier
    for i in range(dice_count):
        roll = random.randint(1, dice_sides)
        Total += roll
        print("Natural roll: " + str(roll))
    return(Total)

def remove_logic(interaction: discord.Interaction, targetDict: dict, condition: str) -> tuple[dict, bool]:
    #'Sanitise' inputs
    condition = condition.strip().lower()
    #Declare some variables
    conditionFound, spellTargetFound, spellFound = False, False, False
    concentratingSpell, concentratingSpellTarget = "", ""
    concentratingSpellConditions = set()
    spellTargetDict = {}
    #remove the condtion
    for condition in targetDict["conditions"]:
        if condition.startswith(condition):
            targetDict["conditions"].remove(condition)
            conditionFound = True
    #Remove its bonuses (if applicable)
            apply_condition_effects(interaction, targetDict, condition, "-")
        if condition.startswith("concentration"): #If were removing concentration, we also need to remove the spell effects 
            concentratingSpell, concentratingSpellTarget = condition.split(":")[1], condition.split(":")[2]
            spellDict, spellFound = getSpellInfo(concentratingSpell) #Get the spell info
            concentratingSpellConditions = set([cond for cond in spellDict["conditions"] if not cond.startswith("#")]) #Remove self inflicted conditions
            if concentratingSpellTarget != target: spellTargetDict, spellTargetFound = getCharacterInfo(interaction, concentratingSpellTarget)
            else: spellTargetDict = targetDict
            for cond in concentratingSpellConditions: #Remove the spells effects
                spellTargetDict["conditions"].remove(cond)
                spellTargetDict = apply_condition_effects(interaction, spellTargetDict, cond, "-")
            if concentratingSpellTarget != target: writeInfo("characters", spellTargetDict)
            else: targetDict = spellTargetDict
            conditionFound = True
    #write info and return the dict so whatever function called this knows about the update.
    writeInfo("characters", targetDict)
    return(targetDict, conditionFound)
remove.autocomplete("target")(autocomplete_characters)

#function to update the autocomplete global lists.
def updateAutocompleteLists():
    #Setup some variables
    global setOfAllAttacks
    global setOfAllCharacters
    global setOfAllSpells
    lineName, fileName = "", ""
    lineNames = []
    DBConnection = sqlite3.connect("Zed\\DNDatabase.db")
    DBCursor = DBConnection.cursor()
    #Update the Attack list
    for fileName in ["attacks", "characters", "spells"]:
        Query = "SELECT Name FROM " + fileName
        DBCursor.execute(Query)
        QueryResult = {line[0] for line in DBCursor.fetchall()}
        if fileName == "attacks": setOfAllAttacks = QueryResult
        elif fileName == "characters": setOfAllCharacters = QueryResult
        elif fileName == "spells": setOfAllSpells = QueryResult
        
#function to roll damage (accounting for crits, resistances, immunities and vulnerabilities)
def calc_damage(interaction: discord.Interaction, attacker: str, target: str, damageDice: list, damageType: list, bonusToHit: int, bonusToDmg: int, contestDC: int, contestDCMod: int, onSave: str = "none", advantage_override: str = "none", applyCrits: bool = True, rollToHitOverride: int = 0) -> tuple[list, list, int, bool, bool, str]:
    #'Sanatise' inputs
    attacker = attacker.strip().lower()
    target = target.strip().lower()
    damageDice[:] = [str(value) for value in damageDice if "d" in value]
    damageType[:] = [str(value) for value in damageType]
    contestDC = max(contestDC, 0)
    contestDCMod = max(contestDCMod, -contestDC)
    onSave = onSave.strip().lower()
    advantage_override = advantage_override.strip().lower()
    rollToHitOverride = min(rollToHitOverride, 20)
    rollToHitOverride = max(rollToHitOverride, 0)
    #Setup some variables
    saved, crit, advantage, disadvantage = False, False, False, False
    rollToHit, alternateRollToHit, diceCount, diceSides = 0, 0, 0, 0
    returnDamages, returnDamageTypes = [], []
    feedbackString = ""
    attackerAdvantageConditions = ["advantage", "helped", "flanking", "hidden", "invisible"] #Attacker has advantage if they have these
    attackerDisadvantageConditions = ["blinded", "frightened", "poisoned", "restrained", "exhaustion3", "disadvantage", "prone", "cursed"] #Attacker has disadvantage if they have these
    targetAdvantageConditions = ["guidingBolt", "flanking", "unaware", "blinded", "paralyzed", "petrified", "prone", "restrained", "stunned", "unconscious", "surprised"] #Attacker has advantage if the target has these
    targetDisadvantageConditions = ["heavilyobscured", "invisible", "dodging"] #Attacker has disadvantage if the target has these
    #Gain relevant information from the attacker and target.
    attackerDict, attackerFound = getCharacterInfo(interaction, attacker)
    targetDict, targetFound = getCharacterInfo(interaction, target)
    #Validate data
    if onSave not in ["miss", "half"]: onSave = "none"
    if advantage_override not in ["advantage", "disadvantage"]: advantage_override = "none"
    if len(damageType) > 1 and len(damageType) != len(damageDice):
        print("calc_damage Error: Damage dice/type format incorrect.\ndamage_dice:" + damage_dice + "\ndamageType:" + damageType)
        return()
    if not attackerFound:
        print("calc_damage Error: Attacker not found. Attacker:" + attacker)
        return()
    if not targetFound:
        print("calc_damage Error: Target not found. Target:" + target)
        return()
    #Deduce (dis)advantage
    advantage = any(cond in attackerAdvantageConditions for cond in attackerDict["conditions"])
    if not advantage: advantage = any(cond in targetAdvantageConditions for cond in targetDict["conditions"]) #If advantage is not already true, check the target conditions
    disadvantage = any(cond in attackerDisadvantageConditions for cond in attackerDict["conditions"])
    if not disadvantage: disadvantage = any(cond in targetDisadvantageConditions for cond in targetDict["conditions"]) #If disadvantage is not already true, check the target's conditions
    advantage, disadvantage = True if advantage_override == "advantage" else advantage, True if advantage_override == "disadvantage" else disadvantage
    #Roll to hit, taking into account (dis)advantage
    rollToHit = rollToHitOverride if rollToHitOverride != 0 else roll_dice(1, 20, bonusToHit)
    if (advantage or disadvantage) and not (advantage and disadvantage): alternateRollToHit = roll_dice(1, 20, bonusToHit)
    if advantage and not disadvantage: rollToHit, feedbackString = max(rollToHit, alternateRollToHit), feedbackString+"Advantage"
    if disadvantage and not advantage: rollToHit, feedbackString = min(rollToHit, alternateRollToHit), feedbackString+"Disadvantage"
    print("^Roll to hit(s)^")
    crit = True if rollToHit-bonusToHit==20 and not "crit" in targetDict["immunities"] else False
    saved = True if rollToHit<contestDC+contestDCMod and not crit else False
    #Roll damage
    for index, dice in enumerate(damageDice):
        diceCount = int(dice.split("d")[0])
        diceSides = int(dice.split("d")[1])
        if crit: diceCount = diceCount*2
        damage = int(roll_dice(diceCount, diceSides, bonusToDmg))
        if bonusToDmg > 0: bonusToDmg = 0 #Apply dmg bonus once
        if saved and onSave == "miss": damage = damage*0
        elif saved and onSave == "half": damage = damage/2
        if damageType[index] in targetDict["immunities"]: damage = damage*0
        elif damageType[index] in targetDict["resistances"]: damage = damage/2
        elif damageType[index] in targetDict["vulnerabilities"]: damage = damage*2
        damage = int(damage) #/2 May make it a float. Doing int() twice may give -1dmg compared to this.
        print("Damage calculated to be: " + str(damage))
        if damageType[index] in returnDamageTypes: returnDamages[returnDamageTypes.index(damageType[index])] += damage
        elif damage > 0:
            returnDamages.append(damage)
            returnDamageTypes.append(damageType[index])
    return(returnDamages, returnDamageTypes, rollToHit, saved, crit, feedbackString)

#Function to write to character file (apply damage and conditions to attacker/caster)
def apply_effects(interaction: discord.Interaction, target: str, damage: int, conditions: list = [], extras: list = []) -> str:
    #'Sanatise' inputs
    target = target.strip().lower()
    conditions[:] = [str(value).strip().lower() for value in conditions]
    extras[:] = [str(value).strip().lower() for value in extras]
    #Setup some variables
    feedbackString, concentratingSpell, concentratingSpellTarget = "", "", ""
    spellFound, spellTargetFound = False, False
    spellDict, spellTargetDict = {}, {}
    concentratingSpellConditions = []
    #Gain relevant information from the target
    targetDict, targetFound = getCharacterInfo(interaction, target)
    #Validate data
    if not targetFound:
        print("apply_effects Error: Target not found. " + target)
        return()
    #Apply damage
    if targetDict["HPTemp"] > 0 and damage > 0:
        targetDict["HPTemp"] = max(0, targetDict["HPTemp"] - damage)
        damage -= max(damage, targetDict["HPTemp"])
    targetDict["HPCurrent"] -= damage
    targetDict["HPCurrent"] = min(targetDict["HPCurrent"], targetDict["HPMax"])
    if targetDict["HPCurrent"] <= 0: feedbackString += "TargetZeroHP"
    #Apply conditions (and effects)
    for condition in conditions:
        targetDict["conditions"].append(condition)
        targetDict = apply_condition_effects(interaction, targetDict, condition)
    #Roll concentration check (if applicable)
    for condition in targetDict["conditions"]:
        if condition.startswith("concentration") and ability_check(interaction, targetDict["name"], "CON", "None") < max(10, damage/2): targetDict = remove_logic(interaction, target, condition)
    #Roll deathsaves (if applicable)
    if "DeathsaveSuccess" in extras: targetDict["deathSaves"] = str(int(targetDict["deathSaves"].split("|")[0])+1)+"|"+targetDict["deathSaves"].split("|")[1]
    if "DeathsaveFail" in extras: targetDict["deathSaves"] = targetDict["deathSaves"].split("|")[0]+"|"+str(int(targetDict["deathSaves"].split("|")[1])+1)
    elif targetDict["HPCurrent"] > 0: targetDict["deathSaves"] = "0|0" #Reset
    #Write to the database and return
    writeInfo("characters", targetDict)
    print("apply_effects Feedback: "+targetDict["name"].title()+" took "+str(damage)+"Dmg, and conditions: "+str(conditions))
    return(feedbackString)

#Function to apply conditional effects e.g. +2Ac or -DexSave
def apply_condition_effects(interaction: discord.Interaction, charDict: dict, condition: str, PosNegOverride: str = "") -> dict:
    #'Sanatise' inputs
    condition = condition.strip().lower()
    PosNegOverride = PosNegOverride.strip().lower()[0:1]
    #Apply the override (given and needed)
    if PosNegOverride == "-" and condition.startswith("+"): condition = "-" + condition[1:]
    elif PosNegOverride == "-" and condition.startswith("-"): condition = "+" + condition[1:]
    elif PosNegOverride == "+" and condition.startswith("-"): condition = "+" + condition[1:]
    elif PosNegOverride == "+" and condition.startswith("+"): condition = "+" + condition[1:]
    else: condition = PosNegOverride + condition
    #Get the BK data for the character
    charDictBK, _ = getCharacterInfo(interaction, charDict["name"], True)
    #Modify the relevant info
    if "ac." in condition: #Modify AC
        acMod = int(condition[0:condition.index("ac")])
        charDict["AC"] = str(int(charDict["AC"])+acMod)
    elif "minac" in condition:
        if "." in condition: minAC = int(condition[condition.index("minac")+5:condition.index(".")])
        else: minAC = int(condition[condition.index("minac")+5:])
        acMod = max(0, int(minAC)-int(charDictBK["AC"]))
        if condition.startswith("-"): acMod = acMod*-1
        charDict["AC"] = str(int(charDict["AC"])+acMod)
    elif "save." in condition: #If the condition affects saveProf
        stat = condition[0:condition.index("save")].upper() #includes the +/-
        if stat.startswith("+"): charDict["savingThrows"].append(stat[1:].upper())
        elif stat.startswith("-") and stat[1:] in charDict["savingThrows"]: charDict["savingThrows"].remove(stat[1:])
    elif "speed." in condition: charDict["speed"] += int(condition[0:condition.index("speed")])
    return(charDict)
    #ADVANCED: MAKE THIS HAVE THE DICT TEXT (e.g. speed) IN THE CONDITION (for now, this works fine)

#Ideas to add:
    """
REJECTED ~~Add Fuzzy Matching with difflib (so minor spelling mistakes don't void a command)~~ This idea is replaced with an autocorrect feature, wont correct spelling errors, but guides the user on input.
Low Priority: Graphics of some kind to make it more user-friendly and exciting to use, somewhat used in encounters
DONE ~~Manual damage/healing & conditions for people who don't use the bot (like)~~
DONE ~~Hiding, Helping, Dodgeing~~
DONE ~~Allow a list of targets to be entered~~
REJECTED(Partly) ~~Give feedback on HP values on attack~~ Reason: Most DM's wont want to reveal their monsters' HP bar to the players. Instead, if the 'character' is not marked with M- (for monster), I will give their remaining hp on turn start.
DONE ~~Add the modifier to the dmg dice text~~
DONE ~~Target yourself~~
DONE ~~Abbility checks at will~~
DONE ~~Create a character~~
DONE ~~Check and remove concentration on dmg effects (and give feedback to the user if it is) ~~
DONE ~~Expand spell list, allow for multiple damage dice sets/damage types (1 dice set for each damage type, like in the ice storm spell)~~
DONE ~~Note: Scope, No combat map, meaning no range. + As little things as hardcoded as possible~~
DONE ~~Saving throws can crit~~ also fixed saving throws being inaccurate in general, and especially inaccurate when rolling more than one damage dice
DONE ~~Manual apply not 'autocorrecting' to a target, and condition applying not working in general~~
DONE ~~Make character creation easier~~
DONE ~~Add 'effects' for spells that apply effects to the character but don't have a duration the same as conditions~~
DONE ~~I have noticed the 'remove_logic' function was removed a while ago without a replacement being given (I will fix this next). Code referencing this nonexistent function will be commented out for now, and some systems won't work as intended.~~
DONE ~~New character file system that includes creature type and size (for grapple, net, and future requirements).~~
DONE ~~Add an autocomplete for attacks/spells, targets and attackers/casters. This is still limited to 25 options, but can work dynamically based on what is already present in the field. Will fix alot of user error and greatly improve user experience (aulthough not strictly required)~~
DONE ~~spells like barkskin that set a minimum AC via a condition~~
Note: /Search has been deprecated (removed)
DONE ~~move to SQL?~~ Easier than I thought :D
DONE ~~Add the versatile property~~
DONE ~~ALSO DELETE THE USER ID FROM THE USERID TABLE IF NO CHARACTERS REFERENCE IT ANYMORE (After/upon character deletion)~~
DONE ~~So far, only the autocomplete is matching users with their characters. A similar thing needs to be done with getting character info (if they're getting info for a user's character that's not in that guild, fail it.)~~
DONE ~~In character creation, allow users to create characters with the same name as other users (a single user must have unique character names)~~
Low Priority (for now): Fully encrypt the UserIDs table (or at least the ID column) it should be secure enough already as only the hosting PC (my PC) has the DNDatabase file, but it does help.
    """
# Start the bot
client.run("MY_TOKEN")
