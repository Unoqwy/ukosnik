# ukosnik

ukosnik is a Python CLI to manage Discord Slash Commands.

<!-- External image URL to make PyPI display it -->
![Insert/update demo output](https://raw.githubusercontent.com/Unoqwy/ukosnik/master/demo/screenshot-update.png "comamnd: ukosnik update <config> -d")

## Installation

**Python 3.6 or higher is required**

Run the command `python3 -m pip install -U ukosnik` to install the CLI.  

You may alternatively clone the repository and install the package from local sources.

## Usage

The following examples assume the environment variable `DISCORD_TOKEN` to be set.  
To make examples simpler, `python3 -m ukosnik` is aliased with `unosnik`, but make sure to use full command path.  

**Register/update slash commands:**  

```sh
# Register/update commands
ukosnik update config_file.yml

# Same but delete oudated commands
ukosnik update config_file.yml -d

# Register/update guild commands
# (very useful for testing since cache updates instantly)
ukosnik update config_file.yml --guild GUILD_ID
```

Please note that updating application commands may take up to 1 hour to refresh, this is an expected Discord behavior.
Read more about it [here](https://discord.com/developers/docs/interactions/slash-commands#registering-a-command).  
**To debug commands, it's recommended to use the `--guild` argument since guild commands update instantly, unlike application-scoped commands.**

*Note: Providing multiple configuration files to merge is not supported yet but is planned.*

**Clear all commands:**  

```sh
# Clear all application commands
ukosnik clear

# Clear all commands from a guild
ukosnik clear --guild GUILD_ID
```

⚠️ No confirmation will be prompted before deleting commands.

## Configuration

Configuration documents are pretty straighforward. They can be either a yml or json file.

For now, the only available field in a configuration document is `commands`. You may provide either an object of commands with the command name as key or a simple list.  
To get a better understanding of how you can register commands, take a look at the [examples](./examples).

