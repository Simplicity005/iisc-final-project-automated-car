import os
import threading

import discord
import rclpy
from dotenv import load_dotenv
from rclpy.node import Node
from std_msgs.msg import String


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
        self.bot.node.publish(command)
        await ctx.respond(f"Sent to robot: `{command}`")


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
        self.node.publish(text)
        self.node.get_logger().info(f"Mention from {message.author}: '{text}'")
        await message.reply(f"Sent to robot: `{text}`")


class DiscordBotNode(Node):
    def __init__(self):
        super().__init__("discord_bot")
        self.publisher = self.create_publisher(String, "bot_input", 10)
        self.bot = DiscordBot(node=self, intents=discord.Intents.all())

    def publish(self, text: str):
        msg = String()
        msg.data = text
        self.publisher.publish(msg)
        self.get_logger().info(f"Published to /bot_input: '{text}'")


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
