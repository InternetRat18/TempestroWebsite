const descriptions = ["Mainly used by the DM to set up a combat encounter. By specifying the characters (+monsters) involved in initiative order, and assigning their character owners. It initiates the encounter within the bot's framework, allowing for turn order, action, health and condition tracking to streamline combat. Actions will be automaticly marked off, but may be done manually aswell.",
	"Lets you add your D&D character for use in every other command. A DM conversation will open, asking you for your character's name, class & level, stats, proficiencies, etc, recording them in the correct format. At the end, there will be a summary of your character before saving. /remove_character can be used if your character does not work as anticipated.",
	"This command allows a player to cast a spell. The user specifies the spell name, the target(s) of the spell, and the caster. The bot then handles all the necessary rolls and modifiers for casting that spell, simplifying the process for new players.",
	"This command facilitates a character's attack. The user inputs the attacker, the weapon, and the target. It then calculates if the attack hits and the damage dealt, streamlining the attack resolution process for players.",
	"When casting spells, a list of targets may be entered for spells with multiple projectiles and AOE. All attacks take into account the vulnerability, resistance and immunities of their target. Additionally, critical hits are taken into account for ease of use, doubling the damage dice rolled.",
	"An optional parameter for /attack, for dual-wielding, sneak attack, divine smite etc. Damage from attacks are applied to the target and if a character reaches zero hp, death saves are then made. Three fails; you're removed from the turn order. Three successes; you're stabilised with 1hp.",
	"Used to perform various combat actions other than attacks. As seen in the example, it can be used for actions like 'Dodge' or 'Hide', abstracting the specific rules for these actions and letting the bot manage their effects on the character and combat.",
	"Using this command allows your character to make an ability or stat check automatically, adding the correct modifier. Similar to other commands, this can be used both in and out of Tempestro's combat encounter framework system.",
	"Roll any custom dice you wish using “XdY”, separated by a plus (e.g., 2d6+1d8), with an optional modifier. The bot will roll each set of dice, providing feedback on each individual roll and automatically applying the modifier to the total.",
	"Often used by players unwilling or unable to use Tempestro, this manually applies effects to characters, such as damage, healing, or conditions. This allows for flexible adjustments during combat, giving the DM control over character states.",
	"The /remove command is used to manually remove a condition from a character, giving control over ongoing effects. The /reset command provides a way to revert the character database to a previous backup state, effectively resetting the combat state."]
const videoFiles = ["CreateCharacter",
	"CreateEncounter",
	"Cast",
	"Attack",
	"CastList",
	"SneakAttack",
	"ActionDodgeHide",
	"RollAbility",
	"RollDice",
	"Apply",
	"RemoveReset"]
const videoCatagories = ["Setup", "Attacks", "Actions and Dice Rolls", "Game Controls"]
var TVIndex = 0
var TVCategory = 0
var min = 0, max = 1

function CommandsTVDial1Click() {
	//Define Category Ranges
	if (TVCategory == 0) {var min = 0, max = 1}
	else if (TVCategory == 1) {var min = 2, max = 5}
	else if (TVCategory == 2) {var min = 6, max = 8}
	else if (TVCategory == 3) {var min = 9, max = 10}
	
	//Increese the index, within the range
	TVIndex = TVIndex + 1;
	if (TVIndex > max) {TVIndex = min}
	
	//Rotate The Dial
	let Dial = document.getElementById("CommandsTVDial1");
	let currentRotation = parseInt(Dial.getAttribute('data-rotation'));
	let newRotation = (TVIndex-min)*90;
	Dial.style.transform = "rotate("+newRotation.toString()+"deg)";
	Dial.setAttribute('data-rotation', newRotation.toString());
	UpdateTV()
}

function CommandsTVDial2Click() {
	//Increese the Category, within the range
	TVCategory = TVCategory + 1;
	if (TVCategory > 3) {TVCategory = 0}
	
	//Update the index to fit the index range
	if (TVCategory == 0) {TVIndex = 0}
	else if (TVCategory == 1) {TVIndex = 2}
	else if (TVCategory == 2) {TVIndex = 6}
	else if (TVCategory == 3) {TVIndex = 9}
	
	//Rotate The Dial
	let newRotation = 90*TVCategory;
	let Dial = document.getElementById("CommandsTVDial2");
	Dial.style.transform = "rotate("+newRotation.toString()+"deg)";
	Dial.setAttribute('data-rotation', newRotation.toString());
	//Reset Dial 1 rotation
	let DialOne = document.getElementById("CommandsTVDial1");
	let newRotationOne = 0;
	DialOne.style.transform = "rotate("+newRotationOne.toString()+"deg)";
	DialOne.setAttribute('data-rotation', newRotationOne.toString());
	UpdateTV()
}

function UpdateTV() {
	//Update the video element to the next in line (of that type)
	let video = document.getElementById("CommandsTVVideo");
	video.src = "Webpage/Videos/Demo-"+videoFiles[TVIndex]+".mp4"
	video.play();
	console.log("Now playing: "+videoFiles[TVIndex]);
	
	//Update Heading and Desc
	let CategoryHeading = document.getElementById("CommandsTVHeadingCategory");
	let Heading = document.getElementById("CommandsTVHeading");
	let Desc = document.getElementById("CommandsTVDesc");
	CategoryHeading.textContent = videoCatagories[TVCategory]
	Heading.textContent= "Command: "+videoFiles[TVIndex]
	Desc.textContent = descriptions[TVIndex]
}

const videos = document.querySelectorAll(".CommandsTVVideo");
videos.forEach(video => {
	video.addEventListener("mouseenter", () => {
	video.loop = true;
	video.play();
	});
	video.addEventListener("mouseleave", () => {
		video.loop = false; // Freeze on last frame
	});
});
