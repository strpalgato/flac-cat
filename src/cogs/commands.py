import argparse
import discord
from discord.ext import commands
import json
import os
import asyncio

# Configuración de FFmpeg
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', # Reconexion opcional
    'options': '-vn'
}

# Clase principal del Bot de Música
class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = []
        self.now_playing = None
        
    @commands.Cog.listener()
    async def on_ready(self):
        print("Cog de Comandos cargado correctamente.")

    @commands.command(help="Conecta el bot al canal de voz.")
    async def join(self, ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
        else:
            await ctx.send("Primero debes estar en un canal de voz.")

    @commands.command(help="Desconecta el bot del canal de voz.")
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            self.song_queue.clear()
        else:
            await ctx.send("El bot no está en un canal de voz.")

    @commands.command(help="Añade una canción por nombre de archivo.")
    async def play(self, ctx, *, filename):
        if not ctx.voice_client:
            await ctx.invoke(self.join)
        filepath = os.path.join("path_to_your_music_files", filename) # Ajusta esta ruta a la carpeta de tus archivos de música.
        if os.path.exists(filepath):
            self.song_queue.append(filepath)
            await ctx.send(f"Se ha añadido {filename} a la cola de reproducción.")
        else:
            await ctx.send("El archivo no se encontró.")
        if not ctx.voice_client.is_playing():
            await self.play_song(ctx)

    async def play_song(self, ctx):
        if not self.song_queue:
            self.now_playing = None
            return
        self.now_playing = self.song_queue.pop(0)
        ctx.voice_client.play(discord.FFmpegPCMAudio(self.now_playing, **ffmpeg_options), after=lambda e: asyncio.run_coroutine_threadsafe(self.play_song(ctx), self.bot.loop))
        await ctx.send(f"Reproduciendo: {os.path.basename(self.now_playing)}")

    @commands.command(help="Pausa la reproducción actual.")
    async def pause(self, ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
        else:
            await ctx.send("No hay ninguna reproducción en curso.")

    @commands.command(help="Reanuda la reproducción.")
    async def resume(self, ctx):
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
        else:
            await ctx.send("La reproducción no está pausada.")

    @commands.command(help="Salta la canción actual.")
    async def skip(self, ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await self.play_song(ctx)
        else:
            await ctx.send("No hay ninguna reproducción en curso para saltar.")

async def setup(client):
    await client.add_cog(Commands(client))


