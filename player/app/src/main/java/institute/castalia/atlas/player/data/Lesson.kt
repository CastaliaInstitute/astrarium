package institute.castalia.atlas.player.data

import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey

@Entity(tableName = "lessons")
data class Lesson(
    @PrimaryKey val id: Long,
    val title: String,
    val band: Int,
    val subject: String,
    val filePath: String,
    val durationSec: Int
)

@Entity(tableName = "queue")
data class QueueItem(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val lessonId: Long,
    val position: Int
)

@Entity(tableName = "progress")
data class Progress(
    @PrimaryKey val lessonId: Long,
    val plays: Int = 0,
    val lastPlayedEpochDay: Int = -1
)
