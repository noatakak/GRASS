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
*/