import discord
from discord.ext import commands
import os
import asyncio
import json
from mutagen import File
from difflib import SequenceMatcher

# Clase principal del Bot de Música
class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = []
        self.now_playing = None
        self.song_database = None
        self.disconnect_timer = None  # Temporizador de desconexión
        
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
            # Cuando el bot se una al canal, iniciamos el temporizador
            self.reset_disconnect_timer()
        else:
            await ctx.send("Primero debes estar en un canal de voz.")

    @commands.command(help="Desconecta el bot del canal de voz.")
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            self.song_queue.clear()
            self.cancel_disconnect_timer()  # Cancela el temporizador de desconexión si existe
            print("Bot desconectado del canal de voz.")
        else:
            await ctx.send("El bot no está en un canal de voz.")
        # Cancela el temporizador de desconexión si se ejecuta el comando !leave
        self.cancel_disconnect_timer()

    @commands.command(help="Añade una canción por nombre de archivo.", aliases=["p", "P"])
    async def play(self, ctx, *, query):
        # Convertir todos los comandos y argumentos a minúsculas
        query = query.lower()
        if not ctx.voice_client:
            await ctx.invoke(self.join)
            # Inicia el temporizador solo si el bot se une al canal de voz
            self.reset_disconnect_timer()
        
        target_songs = self.parse(query)
        self.song_queue.extend(target_songs)

        if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
            await self.play_song(ctx)
        else:
            # Obtener el título de la última canción agregada a la cola
            last_song_data = target_songs[-1]
            last_song_title = last_song_data["title"]
            last_artist = last_song_data["artist"]
            # Crear un mensaje embed para notificar que la canción se ha agregado a la cola
            embed = discord.Embed(
                title="Canción Agregada a la Cola",
                description=f"La canción **{last_song_title}** perteneciente a **{last_artist}** se ha agregado a la cola.",
                color=discord.Color.from_rgb(255, 255, 255)  # Color azul por defecto
            )
            await ctx.send(embed=embed)

    def parse(self, query):
        play_args = query.split(" ")
        target_songs = []

        if "-s" in play_args:
            song_index = play_args.index("-s") + 1
            song_query = " ".join(play_args[song_index:])
            target_songs = self.search_by_song(song_query)

            # Calcular la puntuación de cada canción basada en la similitud del título con la consulta
            for song in target_songs:
                song["score"] = self.calculate_similarity(song["title"], song_query)

            # Ordenar las canciones por puntuación de mayor a menor
            target_songs.sort(key=lambda x: x["score"], reverse=True)

            # Devolver solo la canción con la puntuación más alta
            target_songs = target_songs[:1]

        elif "-a" in play_args:
            artist_index = play_args.index("-a") + 1
            artist_query = " ".join(play_args[artist_index:])
            target_songs.extend(self.search_by_artist(artist_query))
        elif "-l" in play_args:
            album_index = play_args.index("-l") + 1
            album_query = " ".join(play_args[album_index:])
            target_songs.extend(self.search_by_album(album_query))

        return target_songs

    def search_by_artist(self, artist_query):
        return [song for song in self.song_database if artist_query.lower() in song["artist"].lower()]

    def search_by_album(self, album_query):
        return [song for song in self.song_database if album_query.lower() in song["album"].lower()]

    def search_by_song(self, song_query):
        return [song for song in self.song_database if song_query.lower() in song["title"].lower()]

    def calculate_similarity(self, title, query):
        # Calcular la similitud utilizando la función ratio de SequenceMatcher
        similarity = SequenceMatcher(None, title.lower(), query.lower()).ratio()
        return similarity

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

            # Obtener la imagen de la portada del archivo de audio
            audio_file = File(filepath)
            if "APIC:" in audio_file.tags:
                cover_data = audio_file.tags["APIC:"].data
                cover_filename = "cover.jpg"
                with open(cover_filename, "wb") as f:
                    f.write(cover_data)

                # Agregar miniatura al mensaje embed
                file = discord.File(cover_filename, filename="cover.jpg")
                embed = discord.Embed(
                    title="Reproduciendo",
                    description=f"Reproduciendo: {self.now_playing} - {song_data['artist']}",
                    color=discord.Color.from_rgb(255, 255, 255)  # Color azul por defecto
                )
                embed.set_thumbnail(url="attachment://cover.jpg")
                await ctx.send(embed=embed, file=file)
                os.remove(cover_filename)
            else:
                # Crear un mensaje embed sin miniatura si no hay imagen de portada disponible
                embed = discord.Embed(
                    title="Reproduciendo",
                    description=f"**{self.now_playing}** - **{song_data['artist']}**",
                    color=discord.Color.from_rgb(255, 255, 255)  # Color azul por defecto
                )
                await ctx.send(embed=embed)

            # Cancela el temporizador de desconexión
            self.cancel_disconnect_timer()
            
            # Esperar un momento después de conectar antes de reproducir la canción
            await asyncio.sleep(0.5)

            # Cargar el audio
            audio_source = discord.FFmpegPCMAudio(filepath)
            
            # Configurar el volumen del audio
            if ctx.voice_client.source:
                ctx.voice_client.source.volume = 0.5  # Establece el volumen en 0.5 (la mitad)
            
            # Reproducir el audio
            ctx.voice_client.play(audio_source, after=lambda e: self.bot.loop.call_soon_threadsafe(self.song_finished, ctx))
        
        except Exception as e:
            print(f"Error al reproducir la canción: {str(e)}")
            await ctx.send("Ocurrió un error al reproducir la canción.")

    def song_finished(self, ctx):
        # Verificar si hay más canciones en la cola
        if not self.song_queue:
            # Si no hay más canciones, reiniciar el temporizador
            self.reset_disconnect_timer()
        else:
            # Si hay más canciones en la cola, reproducir la siguiente
            asyncio.run_coroutine_threadsafe(self.play_song(ctx), self.bot.loop)

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

    @commands.command(help="Salta la canción actual.", aliases=["s", "S"])
    async def skip(self, ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await self.play_song(ctx)
        else:
            await ctx.send("No hay ninguna reproducción en curso para saltar.")

    def reset_disconnect_timer(self):
        # Cancela el temporizador de desconexión si existe
        self.cancel_disconnect_timer()
        # Programa la desconexión después de 3 minutos
        self.disconnect_timer = self.bot.loop.create_task(self.disconnect_after_timeout())

    def cancel_disconnect_timer(self):
        if self.disconnect_timer:
            self.disconnect_timer.cancel()

    async def disconnect_after_timeout(self):
        remaining_time = 180
        while remaining_time > 0:
            print(f"Tiempo restante para la desconexión automática: {remaining_time} segundos")
            await asyncio.sleep(10)  # Espera 10 segundos antes de verificar de nuevo
            remaining_time -= 10

        print("Bot desconectado por inactividad")
        await self.bot.voice_clients[0].disconnect()

async def setup(client):
    await client.add_cog(Commands(client))
