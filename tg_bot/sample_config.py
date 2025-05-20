import sys
import logging

# Check if the script is run directly and not as a module
if not __name__.endswith("sample_config"):
    print(
        "The README is there to be read. Extend this sample config to a config file, "
        "don't just rename and change values here. Doing that WILL backfire on you.\nBot quitting.",
        file=sys.stderr,
    )
    sys.exit(1)


# Create a new config.py file in the same directory and import, then extend this class.
class Config(object):
    """
    Base configuration class.  All configurations should inherit from this class.
    """

    # Enable or disable logging.  It's generally good to have logging enabled, especially
    # for debugging.  Set to False for production environments where you want to
    # minimize output.
    LOGGER = True

    # **Required Configuration Options:**

    # Your Telegram Bot API key.  This is obtained from BotFather.
    API_KEY = "YOUR KEY HERE"

    # Your Telegram user ID.  This is the ID of the bot's owner.
    # If you don't know it, run the bot and use a command like /id in your
    # private chat with the bot.  The bot will then tell you your user ID.
    OWNER_ID = "YOUR ID HERE"

    # Your Telegram username (without the '@').  This is used in some commands
    # and messages.
    OWNER_USERNAME = "YOUR USERNAME HERE"

    # **Recommended Configuration Options:**

    # The SQLAlchemy database URI.  This is required for any modules that use a database.
    # Example for PostgreSQL: 'postgresql://user:password@host:port/database_name'
    # Example for SQLite: 'sqlite:///local.db'  (for a local file)
    SQLALCHEMY_DATABASE_URI = "sqldbtype://username:password@hostname:port/db_name"

    # The chat ID where messages from 'save from' will be dumped.  This is useful
    # for auditing and ensuring that important messages are not lost.  If set
    # to None, these messages will not be saved.
    MESSAGE_DUMP = None

    # A list of modules to load.  By default, all modules in the modules/
    # directory are loaded.  This option allows you to specify a subset of
    # modules to load.  If you leave it empty, all modules will be loaded.
    # Example:  LOAD = ['admin', 'users', 'bans']
    LOAD = []

    # A list of modules to *not* load.  This is useful for disabling specific
    # modules that you don't want to use.
    NO_LOAD = ["translation", "rss", "sed"]

    # Whether to use webhooks.  Webhooks are the recommended way to receive
    # updates from Telegram in production environments.  If set to False,
    # the bot will use long polling.
    WEBHOOK = False

    # The URL for your webhook.  This is required if WEBHOOK is set to True.
    # It should be the public URL of your server, followed by the bot's token.
    # Example:  URL = 'https://your_domain.com/your_bot_token'
    URL = None

    # **Optional Configuration Options:**

    # A list of user IDs (integers, not usernames) that have sudo (superuser)
    # access to the bot.  Sudo users can bypass many restrictions and
    # perform administrative actions.
    SUDO_USERS = []

    # A list of user IDs (integers, not usernames) that are considered support
    # users.  Support users can perform some administrative actions, such as
    # global bans, but can also be banned themselves.
    SUPPORT_USERS = []

    # A list of user IDs (integers, not usernames) that will not be banned or
    # kicked by the bot.  This is useful for whitelisting staff members or
    # other trusted users.
    WHITELIST_USERS = []

    # A donation link (e.g., PayPal) that is displayed in the /donate command.
    # This allows users to easily donate to support the bot's operation.
    DONATION_LINK = None

    # The path to your SSL certificate.  This is required if you are using
    # webhooks with a self-signed certificate.
    CERT_PATH = None

    # The port on which the bot will listen for incoming connections.
    # The default is 5000, but you can change it if necessary.
    PORT = 5000

    # Whether or not the bot should delete "blue text must click" commands
    # after they are executed.  This can help to keep chats clean.
    DEL_CMDS = False

    # Whether or not global bans should be strictly enforced.  If set to True,
    # users who are globally banned will be automatically kicked from any
    # group where the bot is an admin.
    STRICT_GBAN = False

    # The number of worker threads to use for handling updates.  The default
    # is 8, which is generally a good starting point.  You can adjust this
    # value based on your server's resources and the bot's workload.
    WORKERS = 8

    # The file ID of the sticker to use for bans.  This sticker will be sent
    # when a user is banned.
    BAN_STICKER = "CAADAgADOwADPPEcAXkko5EB3YGYAg"  # banhammer marie sticker

    # Whether to allow commands to be prefixed with '!' as well as '/'.  This
    # can be a matter of personal preference.
    ALLOW_EXCL = False


class Production(Config):
    """
    Configuration class for production environments.  It inherits from the base
    Config class and overrides any settings that are specific to production.
    """

    # Disable logging in production.
    LOGGER = False


class Development(Config):
    """
    Configuration class for development environments.  It inherits from the base
    Config class and overrides any settings that are specific to development.
    """

    # Enable logging in development.
    LOGGER = True
