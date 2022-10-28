import stability_sdk.client as ai_client
import mimetypes

import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation


host = "grpc.stability.ai:443"
api_key = ""

stability_api = ai_client.StabilityInference(host, api_key)


answers = stability_api.generate("a cool cat", width=512, height=512)

for resp in answers:
    for artifact in resp.artifacts:
        if artifact.type != generation.ARTIFACT_IMAGE:
            continue
        ext = mimetypes.guess_extension(artifact.mime)
        contents = artifact.binary
        with open(f"image{ext}", "wb") as f:
            f.write(bytes(contents))
