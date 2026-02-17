import discord
from discord.ext import commands
import aiosqlite
import os

# =============================
# CONFIG
# =============================

TOKEN = os.getenv("MTQ3MzEwNDAyMDkwNTEzNjMzOQ.GkRnAz.tmcou3TKfRqqJ9dnOgEx4aahbYHY4nTqltcTZA")  # Set this in hosting environment
DATABASE = "emails.db"
VERIFIED_ROLE_NAME = "Verified"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# =============================
# DATABASE SETUP
# =============================

async def setup_database():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                email TEXT PRIMARY KEY
            )
        """)
        await db.commit()


# =============================
# BOT READY
# =============================

@bot.event
async def on_ready():
    await setup_database()
    print(f"✅ Bot is online as {bot.user}")


# =============================
# ADMIN COMMANDS
# =============================

@bot.command()
@commands.has_permissions(administrator=True)
async def addemail(ctx, email: str):
    """Add a new verification email (Admin only)"""
    email = email.lower()

    async with aiosqlite.connect(DATABASE) as db:
        try:
            await db.execute(
                "INSERT INTO emails (email) VALUES (?)",
                (email,)
            )
            await db.commit()
            await ctx.send(f"✅ Email `{email}` added successfully.")
        except aiosqlite.IntegrityError:
            await ctx.send("❌ That email already exists in the database.")


@bot.command()
@commands.has_permissions(administrator=True)
async def removeemail(ctx, email: str):
    """Remove an email manually (Admin only)"""
    email = email.lower()

    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "DELETE FROM emails WHERE email = ?",
            (email,)
        )
        await db.commit()

    await ctx.send(f"🗑️ Email `{email}` removed (if it existed).")


@bot.command()
@commands.has_permissions(administrator=True)
async def listemails(ctx):
    """List stored emails (Admin only)"""
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT email FROM emails")
        rows = await cursor.fetchall()

    if not rows:
        await ctx.send("📭 No emails stored.")
        return

    email_list = "\n".join([row[0] for row in rows])
    await ctx.send(f"📧 Stored Emails:\n```{email_list}```")


# =============================
# AUTO DM WHEN USER JOINS
# =============================

@bot.event
async def on_member_join(member):
    try:
        await member.send(
            "👋 Welcome!\n\n"
            "Please reply with the **email you used to purchase** to verify."
        )
    except discord.Forbidden:
        print(f"❌ Could not DM {member.name} (DMs closed)")


# =============================
# HANDLE DM VERIFICATION
# =============================

@bot.event
async def on_message(message):

    # Only handle DMs (not server messages)
    if isinstance(message.channel, discord.DMChannel) and not message.author.bot:

        email = message.content.lower()

        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT email FROM emails WHERE email = ?",
                (email,)
            )
            result = await cursor.fetchone()

            if result:
                # Delete email after successful verification
                await db.execute(
                    "DELETE FROM emails WHERE email = ?",
                    (email,)
                )
                await db.commit()

                # Get server
                guild = bot.guilds[0]
                member = guild.get_member(message.author.id)
                role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)

                if member and role:
                    await member.add_roles(role)
                    await message.channel.send(
                        "✅ You have been successfully verified!"
                    )
                else:
                    await message.channel.send(
                        "⚠️ Verification worked, but role not found."
                    )
            else:
                await message.channel.send(
                    "❌ Email not found or already used."
                )

    await bot.process_commands(message)


# =============================
# ERROR HANDLING
# =============================

@addemail.error
@removeemail.error
@listemails.error
async def admin_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You must be an administrator to use this command.")


# =============================
# START BOT
# =============================

if not TOKEN:
    print("❌ TOKEN environment variable not set.")
else:
    bot.run(TOKEN)
