import asyncio
import os
import discord
from discord import app_commands
from dotenv import load_dotenv
import random

from motor.motor_asyncio import AsyncIOMotorClient

from pokemon import POKEMON
from collections import defaultdict




from PIL import Image
import io, requests



intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)



load_dotenv()
print(repr(os.getenv("MONGO_URI")))

tree = app_commands.CommandTree(client)


mongo = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = mongo["Vulpix"]


@tree.command(name="test", description="test")
async def test(interaction: discord.Interaction):
    for p in POKEMON:
        await interaction.channel.send(p["name"])


@tree.command(name="ping", description="Check if the bot is alive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")


pokedexSize = len(POKEMON)

POKEMON_BY_ROUTE = defaultdict(list)
for p in POKEMON:
    POKEMON_BY_ROUTE[p["route"]].append(p)

POKEMON_BY_RARITY = defaultdict(list)
for p in POKEMON:
    POKEMON_BY_RARITY[p["rarity"]].append(p)


def rarity(x):
    if 0 < x <= 140:
        rarityColor = discord.Color.from_rgb(150, 250, 255)
        return "common", rarityColor
    elif 140 < x <= 190:
        rarityColor = discord.Color.from_rgb(23, 252, 88)
        return "rare", rarityColor
    elif 190 < x <= 199:
        rarityColor = discord.Color.from_rgb(229, 76, 252)
        return "epic", rarityColor
    else:
        rarityColor = discord.Color.from_rgb(255, 234, 0)
        return "legendary", rarityColor




# ===== STARTER COMMAND ============================================================================

@tree.command(name="start", description="Start your journey!")
async def start(interaction: discord.Interaction):
    doc = await db.collection.find_one({"user_id": interaction.user.id})
    if doc is not None:
        await interaction.response.send_message("You've already started your journey!")
        return

    async def pick(button_interaction: discord.Interaction, name: str):
        if button_interaction.user.id != interaction.user.id:
            await button_interaction.response.send_message("This isn't your starter choice!", ephemeral=True)
            return
        await db.collection.update_one(
            {"user_id": interaction.user.id},
            {"$push": {"pokedex": {"species": name, "level": 1, "xp": 0, "count": 1, "fragments": 0}}},
            upsert=True
        )

        starterEmbed = discord.Embed(
            title="New Pokemon Discovered!",
            description=f"{name} has been caught!",
            color=discord.Color.green()
        )

        await interaction.channel.send(embed=starterEmbed)

        await button_interaction.response.send_message(f"You chose {name}! Good luck on your journey.")

        profileDoc = await db.profile.find_one({"user_id": interaction.user.id})
        if profileDoc is None:

            result = await db.profile.update_one({"user_id": interaction.user.id},
                                        {"$set": {"route": 1, "pokedex": f"1/{pokedexSize}", "coins": 0, "PC Level": 1, "Bag Level": 1}},
                                            upsert=True
                                        )

        print(result.raw_result)


    view = discord.ui.View(timeout=30)

    bulbasaur = discord.ui.Button(label="Bulbasaur", style=discord.ButtonStyle.green)
    bulbasaur.callback = lambda i: pick(i, "Bulbasaur")

    charmander = discord.ui.Button(label="Charmander", style=discord.ButtonStyle.red)
    charmander.callback = lambda i: pick(i, "Charmander")

    squirtle = discord.ui.Button(label="Squirtle", style=discord.ButtonStyle.blurple)
    squirtle.callback = lambda i: pick(i, "Squirtle")

    view.add_item(bulbasaur)
    view.add_item(charmander)
    view.add_item(squirtle)

    await interaction.response.send_message("Choose your starter:", view=view)




# ===== PC COMMAND ============================================================================

@tree.command(name="pc", description="View your collection")
async def pc(interaction: discord.Interaction):
    doc = await db.collection.find_one({"user_id": interaction.user.id})
    if doc is None:
        await interaction.response.send_message("You haven't started your journey yet... use the start command!")

    else:
        description = "\n".join(f"- {pokemon['species']} (Lvl {pokemon['level']})" for pokemon in doc['pokedex'])

        pcEmbed = discord.Embed(
            title=f"{interaction.user.display_name}'s Pokemon Collection!",
            description=description,
            color=discord.Color.orange()
        )

        await interaction.response.send_message(embed=pcEmbed)




# ===== BALANCE COMMAND ============================================================================

@tree.command(name="balance", description="View your PokeCoins balance!")
async def balance(interaction: discord.Interaction):
    doc = await db.balance.find_one({"user_id": interaction.user.id})
    if doc is None:

        await db.balance.update_one(
            {"user_id": interaction.user.id},
            {"$set": {"balance": 0}},
            upsert=True
        )

    user = await db.balance.find_one({"user_id": interaction.user.id})

    balanceEmbed = discord.Embed(
        title=f"{interaction.user.display_name}'s PokeCoin Balance!",
        description=f"PokeCoins: {user['balance']}",
        color=discord.Color.orange()
    )

    await interaction.response.send_message(embed=balanceEmbed)




# ===== INVENTORY COMMAND ============================================================================

@tree.command(name="bag", description="View your bag contents!")
async def bag(interaction: discord.Interaction):
    doc = await db.inv.find_one({"user_id": interaction.user.id})
    if doc is None:
        await interaction.response.send_message("Your bag is empty!")
        await interaction.channel.send("Here's one free Pokeball to get started!")


        await db.inv.update_one(
            {"user_id": interaction.user.id},
            {
                "$push":
                    {"pokeball": {"rarity": "Common", "chance": 100}},
                "$set": {"shards": [], "level": 1, "capacity": 5, "count": 1}
            },
            upsert=True
        )

        startingInvEmbed = discord.Embed(
            title="◓ Item found! ◓",
            description="+1 Pokeball (100%)",
            color=discord.Color.green()
        )

        await interaction.channel.send(embed=startingInvEmbed)



    else:

        if doc['count'] >= 5:
            pass

        else:
            await db.inv.update_one(
                {"user_id": interaction.user.id},
                {
                    "$push": {"pokeball": {"rarity": "Common", "chance": 100}},
                    "$inc": {"count": 1}
                },
                upsert=True
            )


        description = "\n".join(f"- {ball['rarity'].capitalize()} Pokeball ({ball['chance']}%)" for ball in doc['pokeball'])

        invEmbed = discord.Embed(
            title=f"{interaction.user.display_name}'s Inventory ({doc['count']}/{doc['capacity']})",
            description=description,
            color=discord.Color.orange()
        )

        await interaction.response.send_message(embed=invEmbed)







# ===== PROFILE COMMAND ============================================================================

@tree.command(name="profile", description="View your profile!")
async def profile(interaction: discord.Interaction):
    doc = await db.profile.find_one({"user_id": interaction.user.id})
    if doc is None:

        await interaction.response.send_message("You haven't started your journey yet... use the start command!")

    else:

        profileEmbed = discord.Embed(
            title=f"{interaction.user.display_name}'s Profile!",
            color=discord.Color.orange()
        )

        profileEmbed.add_field(name="Route", value=doc['route'], inline=False)
        profileEmbed.add_field(name="Pokedex", value=doc['pokedex'], inline=False)
        profileEmbed.add_field(name="Coins", value=doc['coins'], inline=False)
        profileEmbed.add_field(name="PC Level", value=doc['PC Level'], inline=False)
        profileEmbed.add_field(name="Bag Level", value=doc['Bag Level'], inline=False)

        await interaction.response.send_message(embed=profileEmbed)


# ===== EXPLORE COMMAND ============================================================================

@tree.command(name="explore", description="Explore an area for wild Pokémon")
async def explore(interaction: discord.Interaction):

    profileDoc = await db.profile.find_one({"user_id": interaction.user.id})

    route = profileDoc['route']

    available = POKEMON_BY_ROUTE.get(route)

    x = random.randint(1, 200)
    pokemonRarity, pokemonColor = rarity(x)

    availablePokemon = [p for p in available if p["rarity"] == pokemonRarity]


    if not availablePokemon:
        await interaction.response.send_message(f"Error finding pokemon.. try again!")
        return

    else:
        randomPokemon = random.choice(availablePokemon)

        pokedexDoc = await db.collection.find_one({"user_id": interaction.user.id, "pokedex.species": randomPokemon["name"]})


        unknown = False

        if pokedexDoc:

            embedFound = discord.Embed(title=f"You found a {randomPokemon['name']}!",
                                       color=pokemonColor
                                       )

            embedFound.set_image(url=randomPokemon["image"])

            await interaction.response.send_message(embed=embedFound)

        else:

            unknown = True

            img = Image.open(io.BytesIO(requests.get(randomPokemon["image"]).content)).convert("RGBA")
            black = Image.new("RGBA", img.size, (0, 0, 0, 255))
            black.putalpha(img.getchannel("A"))

            buf = io.BytesIO()
            black.save(buf, "PNG")
            buf.seek(0)

            file = discord.File(buf, filename="silhouette.png")
            embedNew = discord.Embed(title="You found a undiscovered Pokemon!",
                                     color=pokemonColor)
            embedNew.set_image(url="attachment://silhouette.png")
            await interaction.response.send_message(embed=embedNew, file=file)



        await asyncio.sleep(1)
        await interaction.channel.send("What do you want to do?")
        await asyncio.sleep(1)


        async def pick(button_interaction: discord.Interaction, name: str):
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("This isn't your encounter!", ephemeral=True)
                return

            def check(m):
                print(repr(m.content), m.author.id, interaction.user.id, m.channel.id, interaction.channel.id)
                return (
                        m.author.id == interaction.user.id
                        and m.channel.id == interaction.channel.id
                        and m.content.isdigit()
                )



            if name == "Battle":
                await button_interaction.response.send_message(f"You engage {randomPokemon['name']} in battle!")






            elif name == "Catch":

                i = 0

                invDoc = await db.inv.find_one({"user_id": interaction.user.id, "pokeball.0": {"$exists": True}})

                pokeballs = [
                    f"{n}. Pokeball ({ball['chance']}%)"
                    for n, ball in enumerate(invDoc["pokeball"], start=1)
                ]


                ballEmbed = discord.Embed(
                    title=f"Pokeballs Available:",
                    description="\n".join(pokeballs),
                    color=discord.Color.orange()
                )

                await interaction.channel.send(embed=ballEmbed)


                try:
                    msg = await client.wait_for("message", check=check, timeout=30)
                    choice = int(msg.content)

                    if 1 <= choice <= len(invDoc["pokeball"]):
                        ball = invDoc["pokeball"][choice - 1]

                        print(choice)
                        print(ball)

                        await interaction.channel.send(f"You chose {ball['chance']}%!")

                        chance = random.randint(1, 100)
                        if chance <= ball["chance"]:
                            if unknown == True:
                                await db.collection.update_one(
                                    {"user_id": interaction.user.id},
                                    {"$push": {
                                        "pokedex": {"species": randomPokemon['name'], "level": 1, "xp": 0, "count": 1, "fragments": 0}}},
                                    upsert=True
                                )
                            else:
                                await db.collection.update_one(
                                    {"user_id": interaction.user.id, "pokedex.species": name},
                                    {"$inc": {"pokedex.$.count": 1}}
                                )

                        index = choice - 1
                        ball = invDoc["pokeball"].pop(index)  # removes it and gives it back to you

                        await db.inv.update_one(
                            {"user_id": interaction.user.id},
                            {
                                "$set": {"pokeball": invDoc["pokeball"]},
                                "$inc": {"count": -1}
                            }
                        )

                    else:
                        await interaction.channel.send(f"That isn't a valid choice.")


                except asyncio.TimeoutError:
                    await interaction.channel.send("You took too long!")





            elif name == "Retreat":
                await button_interaction.response.send_message("You retreat safely.")






        view = discord.ui.View(timeout=30)

        battleButton = discord.ui.Button(label="Battle", style=discord.ButtonStyle.red)
        battleButton.callback = lambda i: pick(i, "Battle")

        catchButton = discord.ui.Button(label="Catch", style=discord.ButtonStyle.blurple)
        catchButton.callback = lambda i: pick(i, "Catch")

        retreatButton = discord.ui.Button(label="Retreat", style=discord.ButtonStyle.green)
        retreatButton.callback = lambda i: pick(i, "Retreat")

        view.add_item(battleButton)
        view.add_item(catchButton)
        view.add_item(retreatButton)

        await interaction.channel.send(view=view)




















@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")

client.run(os.getenv("DISCORD_TOKEN"))