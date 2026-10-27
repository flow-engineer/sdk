# Service error explanations

The documentation website is maintained in the private **flow-engineer/docs** repository and
published at [flow.engineer/docs](https://flow.engineer/docs/unified-messaging-api).

Only `errors/` remains here: one explanation per `ErrorType`. The service copies these files
during generation, embeds them for `explain_error`, and serves them at each error's `doc_url`.
Do not delete or relocate this runtime input without coordinating the service.

When an error changes, update its service explanation and the corresponding published guide
in the docs repository. The API contract remains in `openapi/openapi.yaml`; generated package
and service guidance remains in `agents/`.
