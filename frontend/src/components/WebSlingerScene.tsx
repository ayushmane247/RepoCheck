import { useId } from "react";

function WebSlingerFigure() {
  return <g className="hanging-hero" style={{ transformOrigin: "430px 104px" }}>
    {/* Bent legs and boots */}
    <path d="M426 120 L407 163 L374 176 L354 162 L342 169 L369 194 L417 183 L441 140Z" className="hero-suit-blue" />
    <path d="M428 120 L450 154 L474 165 L487 153 L498 163 L479 185 L442 174 L419 143Z" className="hero-suit-red" />
    <path d="M343 165 L356 155 L378 168 L370 181Z M484 158 L499 149 L510 159 L495 173Z" className="hero-boot" />
    {/* Torso, angled shoulders and articulated arms */}
    <path d="M407 172 Q430 158 453 173 L466 218 L445 247 L413 238 L393 211Z" className="hero-torso" />
    <path d="M404 179 L386 189 L363 216 L346 209 L338 218 L369 237 L398 212Z" className="hero-suit-blue" />
    <path d="M453 179 L473 188 L497 211 L514 204 L523 214 L492 233 L460 210Z" className="hero-suit-red" />
    <path d="M338 211 L350 204 L360 212 L353 226 L340 223Z M511 206 L525 201 L533 211 L523 225 L510 219Z" className="hero-glove" />
    {/* Mask and neck */}
    <path d="M416 239 L444 241 L446 253 L417 254Z" className="hero-neck" />
    <path d="M410 252 Q430 239 451 252 L456 273 L447 296 L431 309 L414 296 L404 274Z" className="hero-mask" />
    <path d="M412 265 Q420 259 427 265 L422 274 L412 273Z M435 265 Q443 259 450 265 L449 273 L439 274Z" className="hero-lens" />
    <path d="M431 274 L431 295 M410 278 Q431 286 452 278 M414 293 Q431 302 448 293" className="hero-mask-detail" />
    {/* Original segmented chest emblem and seam/web lines */}
    <path d="M430 182 L444 200 L430 216 L416 200Z" className="hero-emblem" />
    <path d="M407 183 L420 193 L430 182 L440 193 L454 183 M399 202 L416 200 M461 202 L444 200 M410 224 L430 216 L451 224" className="hero-seam" />
    <path d="M412 252 L421 258 L430 254 L440 258 L451 252 M407 266 L412 273 L404 278 M455 266 L449 273 L456 278" className="hero-mask-detail" />
    <text x="430" y="330" textAnchor="middle" className="hero-mark">RC</text>
  </g>;
}

export function WebSlingerScene({ reducedMotion = false, className = "" }: { reducedMotion?: boolean; className?: string }) {
  const rawId = useId().replaceAll(":", "");
  const clipId = `hero-city-${rawId}`;
  const glowId = `hero-glow-${rawId}`;
  return <svg className={`web-slinger-scene ${className}${reducedMotion ? " is-static" : ""}`} viewBox="0 0 700 430" role="img" aria-label="An original masked web-slinger hangs upside down above a layered night skyline as a scan beam passes over the city.">
    <defs>
      <linearGradient id={glowId} x1="0" y1="0" x2="0" y2="1"><stop stopColor="#1672a5" stopOpacity=".32"/><stop offset="1" stopColor="#08111f" stopOpacity="0"/></linearGradient>
      <clipPath id={clipId}><path d="M0 326 L76 311 L126 319 L193 278 L259 300 L323 250 L382 279 L447 228 L519 263 L579 236 L700 271 V430 H0Z"/></clipPath>
    </defs>
    <path d="M0 0H700V430H0Z" fill={`url(#${glowId})`} />
    <g className="city-back" fill="#101f33" stroke="#24405e" strokeWidth="1.5">
      <path d="M0 311V208H55V151H107V190H145V118H210V205H251V169H300V226H355V140H402V180H455V106H505V200H556V158H612V224H657V173H700V315Z"/>
      <path d="M28 207H53V311H28ZM150 126H202V205H150ZM360 149H398V279H360ZM461 115H499V268H461ZM563 167H606V259H563ZM664 182H691V273H664Z" fill="#122842"/>
    </g>
    <g className="city-mid" fill="#0c1727" stroke="#2a4c6d" strokeWidth="2">
      <path d="M0 350V256H75V213H125V267H176V186H222V285H273V232H320V285H376V190H423V272H472V220H522V302H575V204H624V274H700V350Z"/>
    </g>
    <g className="city-lights">
      {Array.from({ length: 7 }, (_, col) => Array.from({ length: 5 }, (_, row) => <rect key={`${col}-${row}`} x={26 + col * 95} y={238 + row * 20 - (col % 2) * 22} width="4" height="7" rx="1" className={(col + row) % 3 === 0 ? "light-red" : "light-blue"} />))}
    </g>
    <path d="M-10 94 Q177 190 348 97T710 118 M-10 154 Q186 226 361 139T713 164 M37 -10 Q202 88 334 45T683 62" className="city-web" />
    <g className="scan-rings"><ellipse cx="430" cy="105" rx="96" ry="22"/><ellipse cx="430" cy="105" rx="69" ry="15"/></g>
    <path d="M430 -20 L430 116" className="hero-web" />
    <path d="M426 112 Q430 108 434 112 L434 122 L426 122Z" className="hero-web-knot" />
    <g className="hanging-hero-wrap"><WebSlingerFigure /></g>
    <path d="M0 352 Q111 330 198 354T377 350T551 355T700 340V430H0Z" className="rooftop-foreground" />
    <path d="M0 351 Q111 329 198 353T377 349T551 354T700 339" className="roof-edge" />
    <g clipPath={`url(#${clipId})`} className="city-haze"><path d="M0 180H700V430H0Z"/></g>
    <path d="M15 348H685" className="scan-line" />
    <text x="24" y="405" className="scene-label">REPOCHECK FIELD UNIT / NIGHT SHIFT</text>
  </svg>;
}
