from datetime import datetime, timezone, timedelta
from discord_webhook import AsyncDiscordWebhook, DiscordEmbed
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import webhook_ctx
from httpx import AsyncClient, Response
from pathlib import Path

webhook_url: str = Path("webhook_url").read_text()
server_url: str = Path("server_url").read_text()



def time_elapsed_since(time_string: str) -> str:
    time_string = time_string[:19] + 'Z'
    time_difference: timedelta = datetime.now(timezone.utc) - datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%S%z")
    hours: float
    remainder: float
    hours, remainder = divmod(time_difference.total_seconds(), 3600)
    minutes: float
    minutes, _ = divmod(remainder, 60)
    result: str = f"{int(hours)} часов и {int(minutes)} минут"
    return result


async def gen_embed_from_api() -> tuple[bool, DiscordEmbed | None]:
    async with AsyncClient() as client:
        r: Response = await client.get(server_url + '/status')
        if r.status_code != 200:
            return False, None
        json_obj: dict = r.json()
    embed = DiscordEmbed(
        title=json_obj["name"],
        description=(
                f"*Количество игроков:* **{json_obj['players']}**\n"
                f"*Карта:* **{json_obj['map']}**\n"
                f"*ID-Раунда:* **{json_obj['round_id']}**\n"
                + (f"*Раунд идет уже:* **{time_elapsed_since(json_obj['round_start_time'])}**\n"
                   if "round_start_time" in json_obj else "")
        ),
        color="03b2f8"
    )
    return True, embed


async def tick():
    if webhook_ctx.webhook is not None:
        await webhook_ctx.webhook.delete()
    webhook_ctx.webhook = AsyncDiscordWebhook(url=webhook_url)
    embed: tuple[bool, DiscordEmbed | None] = await gen_embed_from_api()
    if not embed[0]:
        print("Error while fetching status from api")
    webhook_ctx.webhook.add_embed(embed[1])

    response = await webhook_ctx.webhook.execute()
    if response.status_code != 200:
        print("Error while sending webhook")


if __name__ == '__main__':
    print("STARTING SS14 SERVER STATUS WEBHOOK!")
    print(f"WEBHOOK URL: {webhook_url}")
    print(f"SERVER URL: {server_url}")
    scheduler: AsyncIOScheduler = AsyncIOScheduler()
    scheduler.add_job(tick, 'interval', seconds=30)
    scheduler.start()

    try:
        asyncio.get_event_loop().run_forever()
    except BaseException as e:
        if webhook_ctx.webhook is not None:
            asyncio.run(webhook_ctx.webhook.delete())
        print(e)
