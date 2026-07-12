import os
import motor.motor_asyncio

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


async def ensure_indexes():
    """Create the uniqueness constraints required by Core storage authority."""
    await db.kernel_runs.create_index("id", unique=True, name="uq_run_id")
    await db.kernel_runs.create_index(
        "creation_command_hash", unique=True, sparse=True,
        name="uq_fork_creation_command",
    )
    await db.kernel_runs.create_index(
        "fork_identity_hash", unique=True, sparse=True,
        name="uq_fork_identity",
    )
    await db.lineage_records.create_index(
        "id", unique=True, name="uq_lineage_record_id",
    )
    await db.lineage_records.create_index(
        "child_lineage_key", unique=True, name="uq_child_lineage",
    )
    await db.accepted_events.create_index(
        [("run_id", 1), ("id", 1)], unique=True, name="uq_run_event_id",
    )
    await db.accepted_events.create_index(
        [("run_id", 1), ("simulation_time", 1), ("order_index", 1)],
        name="ix_run_event_boundary",
    )
    await db.commit_frames.create_index(
        [("run_id", 1), ("tick", 1)], unique=True, name="uq_run_frame_tick",
    )
    await db.entities.create_index(
        [("run_id", 1), ("id", 1)], unique=True, name="uq_run_entity_id",
    )
    await db.rejected_proposals.create_index(
        [("run_id", 1), ("id", 1)], unique=True, name="uq_run_rejection_id",
    )
    # Partial unique: only frames that carry a string identity (legacy frames
    # without the field must not collide on null).
    await db.commit_frames.create_index(
        [("run_id", 1), ("frame_identity_hash", 1)],
        unique=True,
        name="uq_run_frame_identity",
        partialFilterExpression={"frame_identity_hash": {"$type": "string"}},
    )
    await db.recovery_records.create_index(
        "recovery_id", unique=True, name="uq_recovery_id",
    )
