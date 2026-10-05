/** Nothing personal goes to Sentry: no user info, cookies, headers, request bodies or query strings, only the
 *  error and its stack trace. (The API scrubs its own events the same way.) */
export const PRIVATE_DATA_COLLECTION = {
  userInfo: false,
  cookies: false,
  httpHeaders: false,
  httpBodies: [],
  urlQueryParams: false,
} as const;
