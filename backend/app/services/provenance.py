from sqlalchemy.orm import Session

from app.models.artifact import Artifact
from app.models.artifact_version import ArtifactVersion
from app.models.provenance import ProvenanceEvent


def create_artifact(
    db: Session,
    *,
    page_id: int,
    artifact_type: str,
    content: str | None = None,
    file_path: str | None = None,
    created_by: int | None = None,
    generation_method: str = "human",
    model_name: str | None = None,
    model_version: str | None = None,
    metadata: dict | None = None,
) -> Artifact:

    artifact = Artifact(
        page_id=page_id,
        artifact_type=artifact_type,
        version=1,
        content=content,
        file_path=file_path,
        created_by=created_by,
        generation_method=generation_method,
        model_name=model_name,
        model_version=model_version,
        status="created",
        metadata_json=metadata,
    )

    db.add(artifact)
    db.flush()

    version = ArtifactVersion(
        artifact_id=artifact.id,
        version_number=1,
        content=content,
        file_path=file_path,
        created_by=created_by,
        generation_method=generation_method,
        model_name=model_name,
        model_version=model_version,
        change_description="Initial version",
        metadata_json=metadata,
    )

    db.add(version)

    event = ProvenanceEvent(
        artifact_id=artifact.id,
        actor_id=created_by,
        event_type="ARTIFACT_CREATED",
        description=f"{artifact_type} artifact created",
        event_metadata=metadata,
    )

    db.add(event)

    db.flush()

    return artifact

def create_artifact_version(
    db: Session,
    *,
    artifact: Artifact,
    content: str | None = None,
    file_path: str | None = None,
    created_by: int | None = None,
    generation_method: str,
    model_name: str | None = None,
    model_version: str | None = None,
    change_description: str | None = None,
    metadata: dict | None = None,
) -> ArtifactVersion:

    new_version_number = artifact.version + 1

    version = ArtifactVersion(
        artifact_id=artifact.id,
        version_number=new_version_number,
        content=content,
        file_path=file_path,
        created_by=created_by,
        generation_method=generation_method,
        model_name=model_name,
        model_version=model_version,
        change_description=change_description,
        metadata_json=metadata,
    )

    artifact.version = new_version_number

    db.add(version)

    event = ProvenanceEvent(
        artifact_id=artifact.id,
        actor_id=created_by,
        event_type="ARTIFACT_VERSION_CREATED",
        description=change_description,
        event_metadata=metadata,
    )

    db.add(event)

    db.flush()

    return version