"""Ukosnik - Manage Discord slash commands.
Main entry file for command-line usage.
"""

import argparse

import os
import sys
import traceback

from ukosnik.docent import ReadError
from ukosnik.http import Client, HTTPRequestException
import ukosnik.document as ukodoc

cli = argparse.ArgumentParser(description="Manage slash commands easily for your Discord bot")
subparsers = cli.add_subparsers(dest="subcommand")

# args
cli.add_argument("--token", help="bot token (default: ENV['DISCORD_TOKEN'])")
cli.add_argument("--app", type=int, help="application id (default: fetched automatically)")
cli.add_argument("--colored", type=bool, default=True, help="whether some messages should be printed with colors")

# subcommands
cli_update = subparsers.add_parser("update", help="Update application's slash commands")
cli_update.add_argument("config", help="config file")
cli_update.add_argument("-d", action="store_true", help="delete existing commands not present in config")

cli_clear = subparsers.add_parser("clear", help="Clear application's slash commands")

app_args = cli.parse_args()
if not app_args.subcommand:
    cli.print_help()
    sys.exit(0)


def colored(color: str, *args, **kwargs):
    if app_args.colored and len(args) > 0:
        print(f"{color}{args[0]}", *args[1:], "\033[0m", **kwargs)
    else:
        print(*args, **kwargs)


def fail(*args, **kwargs):
    if "file" not in kwargs:
        kwargs["file"] = sys.stderr
    colored("\033[91m", *args, **kwargs)
    sys.exit(1)


def info(*args, **kwargs):
    colored("\033[94m", "I:", *args, **kwargs)


def ok(*args, **kwargs):
    colored("\033[92m", "OK:", *args, **kwargs)


token = app_args.token or os.environ.get("DISCORD_TOKEN")
if token is None:
    fail(
        "Bot token is required! You can pass it through the DISCORD_TOKEN",
        "env variable or the '--token' argument.",
        file=sys.stderr,
    )
if " " not in token:
    token = f"Bot {token}"

if app_args.subcommand == "update":
    try:
        # TODO error messages with context
        with open(app_args.config, "r") as config_file:
            try:
                _, ext = os.path.splitext(app_args.config)
                if ext in (".yml", ".yaml"):
                    from yaml import full_load as read_file
                else:
                    raise Exception("Unsupported file type '%s'." % ext)
                doc_dict = read_file(config_file)
            except Exception:
                traceback.print_exc()
                fail("Could not read config file.")

            try:
                document = ukodoc.read(doc_dict)
                del doc_dict
            except ReadError as err:
                fail(f"Could not parse configuration file.\nError: {err}")
    except IsADirectoryError:
        fail("Configuration file cannot be a directory.")
    except FileNotFoundError:
        fail("Configuration file not found.")

    if len(document.commands) > 0:
        info(f"Loaded {len(document.commands)} command(s).")
    else:
        info("No commands were loaded (empty 'commands' list).")

try:
    client = Client(token)
    application_id = app_args.app or client.get_application_id()
    info(f"Using application ID {application_id}.")
    if app_args.subcommand == "update":
        # doc is defined but ls struggles to know it
        document = document # type: ignore

        existing_commands = client.fetch_commands(application_id)
        info(f"Fetched {len(existing_commands)} existing commands.")

        existing_command_names = set(map(lambda command: command["name"], existing_commands))
        command_names = set(map(lambda command: command["name"], document.commands))

        step = 1
        print(f"[{step}] Updating commands...")
        for command in document.commands:
            command_name = command["name"]
            try:
                client.upsert_command(application_id, command)
                verb = "Updated" if command_name in existing_command_names else "Inserted"
                ok(f"{verb} command '{command_name}' successfully.")
            except HTTPRequestException as err:
                fail(f"Failed to upsert command {command_name}.\nError: {err}")
        else:
            if len(document.commands) == 0:
                info("No commands to insert/update.")

        if app_args.d:
            step += 1
            print(f"[{step}] Delete flag detected, deleting former commmands...")
            former_commands = [cmd for cmd in existing_commands if cmd["name"] not in command_names]
            for command in former_commands:
                command_name = command["name"]
                try:
                    client.delete_command(application_id, command["id"])
                    ok(f"Deleted command '{command_name}' ({command['id']}) sucessfully.")
                except HTTPRequestException as err:
                    fail(f"Failed to delete command {command_name}.\nError: {err}")
            else:
                if len(former_commands) == 0:
                    info("No former commands to delete.")
        print("Slash commands updated successfully.")
    elif app_args.subcommand == "clear":
        existing_commands = client.fetch_commands(application_id)
        info(f"Fetched {len(existing_commands)} existing commands.")

        print("Clearing all slash commands...")
        for command in existing_commands:
            command_name = command["name"]
            try:
                client.delete_command(application_id, command["id"])
                ok(f"Deleted command '{command_name}' ({command['id']}) sucessfully.")
            except HTTPRequestException as err:
                fail(f"Failed to delete command {command_name}.\nError: {err}")
        print("Cleared slash commands successfully.")

except HTTPRequestException as err:
    fail(f"An error was raised while performing a request.\nError: {err}")
