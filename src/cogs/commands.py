import discord
from discord.ext import commands
import os
import asyncio
import json

# Clase principal del Bot de Música
class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = []
        self.now_playing = None
        self.song_database = None
        self.leave_timer = None  # Temporizador para desconectar el bot del canal

    @commands.Cog.listener()
    async def on_ready(self):
        print("Cog de Comandos cargado correctamente.")
        self.load_song_database()  # Cargamos la base de datos de canciones cuando el bot está listo

    def load_song_database(self):
        # Cargamos la base de datos de canciones desde el archivo JSON
        with open("data/song_database.json", "r") as f:
            self.song_database = json.load(f)

    @commands.command(help="Conecta el bot al canal de voz.")
    async def join(self, ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
            print(f"Bot conectado al canal de voz: {channel}")
        else:
            await ctx.send("Primero debes estar en un canal de voz.")

    @commands.command(help="Desconecta el bot del canal de voz.")
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            self.song_queue.clear()
            print("Bot desconectado del canal de voz.")
            self.cancel_leave_timer()  # Cancela el temporizador al salir del canal
        else:
            await ctx.send("El bot no está en un canal de voz.")

    @commands.command(help="Añade una canción por nombre de archivo.")
    async def play(self, ctx, *, query):
        if not ctx.voice_client:
            await ctx.invoke(self.join)
        
        target_songs = self.parse(query)
        self.song_queue.extend(target_songs)

        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
            await self.play_song(ctx)
        else:
            await ctx.send("La canción se ha agregado a la cola.")

    def parse(self, query):
        play_args = query.split(" ")
        target_songs = []
        # Procesamos los argumentos
        if "--artist" in play_args:
            artist_index = play_args.index("--artist") + 1
            artist_query = " ".join(play_args[artist_index:])
            target_songs.extend(self.search_by_artist(artist_query))
        if "--album" in play_args:
            album_index = play_args.index("--album") + 1
            album_query = " ".join(play_args[album_index:])
            target_songs.extend(self.search_by_album(album_query))
        if "--song" in play_args:
            song_index = play_args.index("--song") + 1
            song_query = " ".join(play_args[song_index:])
            target_songs.extend(self.search_by_song(song_query))
        return target_songs

    def search_by_artist(self, artist_query):
        return [song for song in self.song_database if artist_query.lower() in song["artist"].lower()]

    def search_by_album(self, album_query):
        return [song for song in self.song_database if album_query.lower() in song["album"].lower()]

    def search_by_song(self, song_query):
        return [song for song in self.song_database if song_query.lower() in song["title"].lower()]

    async def play_song(self, ctx):
        try:
            if not self.song_queue:
                self.now_playing = None
                return
            song_data = self.song_queue.pop(0)
            filepath = song_data["filepath"]
            print(f"Ruta del archivo: {filepath}")  # Imprime la ruta del archivo
            self.now_playing = song_data["title"]
            print(f"Reproduciendo: {self.now_playing}")
            await ctx.send(f"Reproduciendo: {self.now_playing}")

            # Esperar un momento después de conectar antes de reproducir la canción
            await asyncio.sleep(0.5)

            # Cargar el audio
            audio_source = discord.FFmpegPCMAudio(filepath)
            
            # Configurar el volumen del audio
            if ctx.voice_client.source:
                ctx.voice_client.source.volume = 0.5  # Establece el volumen en 0.5 (la mitad)
            
            # Reproducir el audio
            ctx.voice_client.play(audio_source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_song(ctx), self.bot.loop))

            # Inicia el temporizador para desconectar el bot después de 5 minutos sin reproducción
            self.start_leave_timer(ctx)
        
        except Exception as e:
            print(f"Error al reproducir la canción: {str(e)}")
            await ctx.send("Ocurrió un error al reproducir la canción.")

    def start_leave_timer(self, ctx):
        self.cancel_leave_timer()  # Cancela el temporizador existente si lo hay
        self.leave_timer = self.bot.loop.call_later(300, self.leave_after_timeout, ctx)

    def cancel_leave_timer(self):
        if self.leave_timer:
            self.leave_timer.cancel()

    async def leave_after_timeout(self, ctx):
        if ctx.voice_client.is_playing():
            return  # Si se está reproduciendo una canción, no desconectarse
        await ctx.voice_client.disconnect()
        self.song_queue.clear()
        print("Bot desconectado del canal de voz por inactividad.")

    @commands.command(help="Pausa la reproducción actual.")
    async def pause(self, ctx):
        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            ctx.voice_client.pause()
            await ctx.send("Reproducción pausada.")
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
