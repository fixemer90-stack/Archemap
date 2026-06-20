// Browser auth is cookie-first. JWT cookies are HttpOnly and intentionally not
// readable from JavaScript. Keep this module for future non-auth cookie helpers;
// do not add access/refresh token readers or writers here.
export {};
