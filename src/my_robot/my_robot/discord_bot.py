import asyncio
import os
import threading
import time

import discord
import rclpy
from dotenv import load_dotenv
from rclpy.node import Node

from my_robot_msgs.srv import ParseIntent


class BotCommands(discord.Cog):
    def __init__(self, bot: "DiscordBot"):
        self.bot = bot

    @discord.slash_command(name="hello", description="Say hello to the bot")
    async def hello(self, ctx: discord.ApplicationContext):
        await ctx.respond("Hey!")

    @discord.slash_command(name="run", description="Send a command to the robot")
    async def run_command(
        self,
        ctx: discord.ApplicationContext,
        command: discord.Option(str, "What should the robot find?"),
    ):
        await ctx.defer()
        result = await self.bot.node.call_parse_intent(command)
        if result.success:
            await ctx.followup.send(f"Searching for: `{result.message}`")
        else:
            await ctx.followup.send(f"Error: {result.message}")


class DiscordBot(discord.Bot):
    def __init__(self, node: "DiscordBotNode", **kwargs):
        super().__init__(**kwargs)
        self.node = node
        self.add_cog(BotCommands(self))

    async def on_ready(self):
        self.node.get_logger().info(f"{self.user} is ready and online!")

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if self.user not in message.mentions:
            return
        text = message.content.replace(f"<@{self.user.id}>", "").strip()
        if not text:
            return
        self.node.get_logger().info(f"Mention from {message.author}: '{text}'")
        result = await self.node.call_parse_intent(text)
        if result.success:
            await message.reply(f"Searching for: `{result.message}`")
        else:
            await message.reply(f"Error: {result.message}")


# TODO MAKE IT EMBED


class DiscordBotNode(Node):
    def __init__(self):
        super().__init__("discord_bot")
        self.cli = self.create_client(ParseIntent, "parse_intent")
        self.bot = DiscordBot(node=self, intents=discord.Intents.all())

    async def call_parse_intent(self, text: str) -> ParseIntent.Response:
        req = ParseIntent.Request()
        req.command = text

        if not self.cli.wait_for_service(timeout_sec=5.0):
            self.get_logger().error("parse_intent service not available")
            res = ParseIntent.Response()
            res.success = False
            res.message = "The LLM parser is not running."
            return res

        future = self.cli.call_async(req)

        loop = asyncio.get_event_loop()

        def wait_for_result():
            while not future.done():
                time.sleep(0.05)
            return future.result()

        return await loop.run_in_executor(None, wait_for_result)


def main(args=None):
    load_dotenv()
    rclpy.init(args=args)
    node = DiscordBotNode()
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()
    node.bot.run(os.getenv("TOKEN"))
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
