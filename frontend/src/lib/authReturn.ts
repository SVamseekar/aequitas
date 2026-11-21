/** Same recognised-route restriction as the OAuth callback; never an external target. */
export function authReturnPath(value:string|null):string {
 if(!value||value.length>4096||value.includes('\\')||[...value].some(char=>char.charCodeAt(0)<32)||!value.startsWith('/')||value.startsWith('//'))return '/app/england'
 const url=new URL(value,'http://local.invalid')
 return /^(?:\/app\/(?:england|ireland|netherlands|france)(?:\/(?:equity|access|service|network|correlations|economy|policy|scenarios|studio|compare|reach|time|ops))?\/?|\/(?:saved|notes|regions|conversations|profile)|\/invite\/[A-Za-z0-9_-]{1,256})$/.test(url.pathname)?value:'/app/england'
}
