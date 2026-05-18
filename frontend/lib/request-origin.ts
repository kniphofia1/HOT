export function getRequestOrigin(request: Request): string {
  const requestUrl = new URL(request.url);
  const forwardedHost = request.headers.get("x-forwarded-host");
  const forwardedProto = request.headers.get("x-forwarded-proto");
  const host = firstHeaderValue(forwardedHost) ?? request.headers.get("host") ?? requestUrl.host;
  const protocol = firstHeaderValue(forwardedProto) ?? requestUrl.protocol.replace(":", "");

  return `${protocol}://${host}`;
}

function firstHeaderValue(value: string | null): string | null {
  return value?.split(",")[0]?.trim() || null;
}
