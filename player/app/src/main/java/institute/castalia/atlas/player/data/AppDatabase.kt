package institute.castalia.atlas.player.data

import android.content.Context
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Room
import androidx.room.RoomDatabase

@Dao
interface LessonDao {
    @Query("SELECT * FROM lessons ORDER BY band, id")
    fun all(): List<Lesson>

    @Query("SELECT * FROM lessons WHERE band = :band ORDER BY id")
    fun byBand(band: Int): List<Lesson>

    @Query("SELECT * FROM lessons WHERE id = :id")
    fun byId(id: Long): Lesson?

    @Query("SELECT * FROM lessons WHERE subject = 'sleep-music' LIMIT 1")
    fun sleepMusic(): Lesson?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    fun upsertAll(lessons: List<Lesson>)
}

@Dao
interface QueueDao {
    @Query("SELECT * FROM queue ORDER BY position")
    fun all(): List<QueueItem>

    @Insert
    fun insertAll(items: List<QueueItem>)

    @Query("DELETE FROM queue")
    fun clear()
}

@Dao
interface ProgressDao {
    @Query("SELECT * FROM progress WHERE lessonId = :id")
    fun byId(id: Long): Progress?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    fun upsert(progress: Progress)
}

@Database(
    entities = [Lesson::class, QueueItem::class, Progress::class],
    version = 1
)
abstract class AppDatabase : RoomDatabase() {

    abstract fun lessons(): LessonDao
    abstract fun queue(): QueueDao
    abstract fun progress(): ProgressDao

    companion object {
        @Volatile
        private var instance: AppDatabase? = null

        fun get(ctx: Context): AppDatabase =
            instance ?: synchronized(this) {
                instance ?: Room.databaseBuilder(
                    ctx.applicationContext,
                    AppDatabase::class.java,
                    "atlas.db"
                )
                    .fallbackToDestructiveMigration()
                    .build()
                    .also { instance = it }
            }
    }
}
