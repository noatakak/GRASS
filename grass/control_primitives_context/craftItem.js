// This method can be used without a crafting table if no crafting table is needed.
async function craftItem(bot, name, count = 1) {
    const item = mcData.itemsByName[name];
    const recipe = bot.recipesFor(item.id, null, 1)[0];
    await bot.craft(recipe, count, null);
}
