// You must place a crafting table before calling this function
async function craftItem(bot, name, count = 1) {
    const item = mcData.itemsByName[name];
    const craftingTable = bot.findBlock({
        matching: mcData.blocksByName.crafting_table.id,
        maxDistance: 32,
    });
    await bot.pathfinder.goto(
        new GoalLookAtBlock(craftingTable.position, bot.world)
    );
    const recipe = bot.recipesFor(item.id, null, 1, craftingTable)[0];
    await bot.craft(recipe, count, craftingTable);
}



/*
Add back later maybe explore until

Explore until find any terracotta block, use Vec3(1, 0, 1) because terracotta is usually on the surface
let terracotta = await exploreUntil(bot, new Vec3(1, 0, 1), 60, () => {
    const terracotta = bot.findBlock({
      matching: block => {
        return block.name.includes("terracotta");
      },
      maxDistance: 32
    });
    return terracotta;
});

async function craftDoor(bot) {
  // Check if the bot has wood in its inventory
  const planks = bot.inventory.findInventoryItem(matching: block => {
        return block.name.includes("planks");
      },);

  // If not, collect planks
  if (!planks) {
    await craftPlanks(bot);
  }

  // Craft wooden planks
  await craftItem(bot, mcData.blocksByName.planks.id, 1);
  bot.chat("Wooden planks crafted.");
}


You are a helpful assistant that tells me the next immediate task to do in Minecraft.
Your goal is to find as many unique items as possible and learn as many unique tasks as possible.

//11:43
You have just joined a world in minecraft and are given a list of usable skills. Using only these skills and assuming that you know nothing else
and have access to no other resources, write the next least difficult skill within the game.

/11:54
and should complete the first skill needed to progress in the game, assuming in this case
that you have no skills or items in your inventory while still following all the rules below.

/12:09
2) If you were given no skills, you have just begun the game, and should write the first skill needed when the game begins.


/12:24
10) The next skill should follow a concise format, such as "Craft [block]", "Obtain [block]", "Kill [mob]", "Equip [item]" etc. It should be a single phrase. Do not propose multiple skills at the same time. Do not include quantities.


//old
I will give you the following information:
Usable tasks: ...
Unusable tasks: ...

If you were given no usable tasks, you have just begun the game and should complete the first task necessary when the game begins,
assume that you have no tasks or items in your inventory.

You must follow the following criteria:
1) You should act as a mentor and guide me to the next task based on my current learning progress, incrementally increasing the complexity of the task.
2) Do not write a task that shares the name/purpose of any tasks given to you.
3) Only write a task if you have a prerequisite task for every item you might need to complete the task.
4) The new task should be specific enough so that an outside agent could execute it according to the knowledge you have provided.
5) tasks should have specific and repeatable results.
6) Do not make up prerequisite tasks. Only use the task names given in the usable task list, to fill your new prerequisite list.
7) Ensure that your new task uses at least one of the tasks given in the list as a prerequisite.
8) Never use an unusable task as a prerequisite or attempt to recreate an unusable task.
9) The next task should follow a concise naming format, such as "Obtain [block]", "Kill [mob]", "Equip [item]" etc. It should be a single phrase. Do not propose multiple tasks at the same time. Do not include quantities as this task should produce the minimum quantity possible.

The answer should be returned only in the form:
{
    "name": "a task name using the naming conventions provided"
    "knowledge": "specific instructions on how to complete the task at hand, including materials, items, or tools used"
    "prerequisites": ["a list of tasks needed to obtain all required materials, items, or tools, selected only from the list of usable tasks"]
}






Your description must adhere to the following rules.
1) You should act as a mentor and guide me to the next skill based on my current learning progress. Steps should be very incremental in difficulty.
2) Your guide must use all the "Mandatory Skills".
3) If you are given nothing in the "Mandatory Skills", then you have just begun the game, and should write the first skill needed when the game begins.
4) Do not write a description for a skill that accomplishes the same things as anything in the "Previous Descriptions" list.
5) Your description should describe the process of using these "Mandatory Skills" to complete a new skill.
6) Your description should include specific minimum quantities of all materials, items, and tools necessary to complete the new skill.
7) Your skill should be as easy as possible, while still accomplishing something new.
8) Do not describe the contents of the "Mandatory Skills" in your description.


*/