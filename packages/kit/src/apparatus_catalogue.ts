// The apparatus catalogue (W16, D-66): every part `Synapse.apparatus` can draw, the channels it has, and when a Plan should use it. Data only, no DOM, so the manifest
// build can read it and the API can check a Plan against it. A channel draws a number it is given and never prints one:
//   fraction  the value over the part's `full` (a beaker's level, a flame's size, a planet's speed); full is the value drawn as a full beaker, the biggest flame
//   angle     a slope in degrees, 0 to 60 (drawn at that angle)
//   ph        a pH, 0 to 14 (drawn in universal-indicator colours)

export type ChannelType = "fraction" | "angle" | "ph";

export interface ChannelInfo {
  type: ChannelType;
  doc: string;
  optional?: boolean;
  /** Units the bound value must have, when the channel means one quantity only. Empty: any unit, judged by its scale. */
  units?: string[];
}

/** Where a channel can be grabbed on the drawing (W17, D-69), in the part's 120 by 140 drawing units. A line runs from the point drawn at value 0 to the point drawn at full;
 * a pivot is for an angle channel: the grip sits `radius` from the pivot along the slope. Only channels a student would handle have one (the liquid, the plunger, the trolley). */
export type Grab = { from: [number, number]; to: [number, number] } | { pivot: [number, number]; radius: number };

export interface PartInfo {
  group: "glassware" | "heat" | "measurement" | "mechanics" | "electricity" | "waves" | "space" | "particles" | "biology" | "chemistry";
  doc: string;
  useWhen: string;
  channels: Record<string, ChannelInfo>;
  /** The channels with a grip, when the channel is bound to a slider. */
  grabs?: Record<string, Grab>;
}

const level: ChannelInfo = { type: "fraction", doc: "how full it is: the liquid's volume (or any amount) over full" };
const bubbles: ChannelInfo = { type: "fraction", optional: true, doc: "how hard it fizzes: more and faster bubbles as the value nears full (a gas given off, a rate)" };

export const APPARATUS: Record<string, PartInfo> = {
  beaker: { group: "glassware", doc: "A beaker of liquid.", useWhen: "a liquid that is measured, mixed, heated or diluted; a reaction that gives off gas (with bubbles)", channels: { level, bubbles }, grabs: { level: { from: [60, 130], to: [60, 38] } } },
  flask: { group: "glassware", doc: "A conical flask of liquid.", useWhen: "a titration flask, a reaction flask, a culture", channels: { level, bubbles }, grabs: { level: { from: [60, 132], to: [60, 52] } } },
  test_tube: { group: "glassware", doc: "A test tube of liquid.", useWhen: "a small-scale reaction, a food test, fermentation, an enzyme test", channels: { level, bubbles }, grabs: { level: { from: [60, 126], to: [60, 30] } } },
  cylinder: { group: "glassware", doc: "A measuring cylinder with marks (no numbers on it).", useWhen: "measuring a volume of liquid; gas collected over water", channels: { level }, grabs: { level: { from: [60, 126], to: [60, 16] } } },
  solution: { group: "chemistry", doc: "A beaker of solution with dissolved particles drawn in it.", useWhen: "concentration, dilution, dissolving, solubility", channels: { concentration: { type: "fraction", doc: "how concentrated: more particles drawn as the value nears full" }, level: { ...level, optional: true } }, grabs: { level: { from: [60, 130], to: [60, 38] } } },
  indicator: { group: "chemistry", doc: "A tube of solution in universal-indicator colours.", useWhen: "acids and alkalis, pH, neutralisation", channels: { ph: { type: "ph", doc: "the pH, 0 to 14", units: ["pH"] } } },
  syringe: { group: "glassware", doc: "A gas syringe whose plunger moves out as the gas grows.", useWhen: "the volume of a gas: collected in a reaction, compressed (Boyle's law), heated", channels: { volume: { type: "fraction", doc: "the gas volume over full" } }, grabs: { volume: { from: [16.5, 65], to: [94.5, 65] } } },
  burner: { group: "heat", doc: "A Bunsen burner whose flame grows with the heat.", useWhen: "heating: specific heat capacity, a reaction rate with temperature, latent heat", channels: { heat: { type: "fraction", doc: "the heating power or heat supplied over full" } }, grabs: { heat: { from: [60, 76], to: [60, 22] } } },
  thermometer: { group: "measurement", doc: "A thermometer whose column rises (no scale numbers).", useWhen: "a temperature that changes: heating, cooling, an exothermic reaction", channels: { temperature: { type: "fraction", doc: "the temperature (or its rise) over full" } }, grabs: { temperature: { from: [60, 112], to: [60, 18] } } },
  balance: { group: "measurement", doc: "An electronic balance with a load on its pan and a bar display.", useWhen: "a mass that is measured or changes: a reaction that loses gas, osmosis, food", channels: { mass: { type: "fraction", doc: "the mass over full" } }, grabs: { mass: { from: [60, 90], to: [60, 56] } } },
  gauge: { group: "measurement", doc: "A dial gauge whose needle swings with the value (no numbers on its face).", useWhen: "any pressure, force, speed or meter reading", channels: { value: { type: "fraction", doc: "the reading over full" } } },
  weights: { group: "mechanics", doc: "Slotted masses stacked on a hanger.", useWhen: "a load or weight that is added in steps", channels: { load: { type: "fraction", doc: "the load over full: up to eight masses drawn" } }, grabs: { load: { from: [60, 128], to: [60, 38] } } },
  spring: { group: "mechanics", doc: "A coiled spring that stretches.", useWhen: "an extension, a compression, elastic potential energy", channels: { extension: { type: "fraction", doc: "the extension over full" } }, grabs: { extension: { from: [60, 55], to: [60, 125] } } },
  trolley: { group: "mechanics", doc: "A trolley on a track.", useWhen: "motion: distance, speed, acceleration, momentum, a collision", channels: { position: { type: "fraction", doc: "how far along the track" }, speed: { type: "fraction", optional: true, doc: "how fast its wheels turn" } }, grabs: { position: { from: [23, 93], to: [97, 93] } } },
  ramp: { group: "mechanics", doc: "A block on a slope.", useWhen: "a slope: forces on an inclined plane, friction, resolving forces", channels: { angle: { type: "angle", doc: "the slope's angle, 0 to 60 degrees", units: ["deg"] } }, grabs: { angle: { pivot: [10, 126], radius: 55 } } },
  pendulum: { group: "mechanics", doc: "A simple pendulum that swings.", useWhen: "oscillation, period, energy changes in a swing", channels: { length: { type: "fraction", doc: "the string's length over full (a longer string swings more slowly)" } }, grabs: { length: { from: [60, 39], to: [60, 123] } } },
  bulb: { group: "electricity", doc: "A light bulb that glows.", useWhen: "electrical power, energy, a brighter or dimmer lamp", channels: { brightness: { type: "fraction", doc: "the power, current or energy over full" } } },
  circuit: { group: "electricity", doc: "A circuit loop with a cell, a resistor and a lamp; charge flows round it.", useWhen: "current, voltage, resistance, Ohm's law, series and parallel circuits", channels: { current: { type: "fraction", doc: "the current over full: faster flow, brighter lamp" } } },
  coils: { group: "electricity", doc: "A transformer: two coils on an iron core.", useWhen: "transformers, electromagnetic induction", channels: { primary: { type: "fraction", doc: "the primary turns over full" }, secondary: { type: "fraction", doc: "the secondary turns over full" } }, grabs: { primary: { from: [30, 36], to: [30, 99] }, secondary: { from: [90, 36], to: [90, 99] } } },
  wave: { group: "waves", doc: "A travelling wave.", useWhen: "wave speed, frequency, wavelength, amplitude, sound and light as waves", channels: { amplitude: { type: "fraction", optional: true, doc: "the amplitude over full (drawn at half height when not bound)" }, wavelength: { type: "fraction", doc: "the wavelength over full" }, frequency: { type: "fraction", optional: true, doc: "how fast it travels across" } }, grabs: { wavelength: { from: [20, 112], to: [80, 112] } } },
  orbit: { group: "space", doc: "A planet or satellite going round a star or planet.", useWhen: "gravitation, orbits, satellites, the solar system", channels: { speed: { type: "fraction", doc: "how fast it goes round" }, radius: { type: "fraction", optional: true, doc: "the orbit's radius over full" } }, grabs: { radius: { from: [84, 70], to: [114, 70] } } },
  particles: { group: "particles", doc: "A box of gas particles that jostle.", useWhen: "kinetic theory: temperature, gas pressure, states of matter, diffusion", channels: { speed: { type: "fraction", doc: "how fast they move: the temperature or kinetic energy over full" } } },
  nuclei: { group: "particles", doc: "A grid of nuclei, some still undecayed.", useWhen: "radioactive decay, half-life, activity", channels: { remaining: { type: "fraction", doc: "the share still undecayed: the amount left over full" } } },
  leaf: { group: "biology", doc: "A water plant in light, giving off oxygen bubbles.", useWhen: "photosynthesis: light intensity, rate, compensation point", channels: { light: { type: "fraction", doc: "the light intensity over full" }, rate: { type: "fraction", optional: true, doc: "the rate of photosynthesis over full: more bubbles" } }, grabs: { light: { from: [18, 14], to: [58, 38] } } },
  cell: { group: "biology", doc: "A cell that grows or shrinks.", useWhen: "cell size, surface area to volume, osmosis, magnification", channels: { size: { type: "fraction", doc: "the cell's size over full" } }, grabs: { size: { from: [70, 70], to: [118, 70] } } },
  field: { group: "biology", doc: "A field with a quadrat and plants in it.", useWhen: "population, quadrat sampling, density, distribution", channels: { density: { type: "fraction", doc: "the population density over full: up to forty plants drawn" } } },
};

export const MAX_APPARATUS_PARTS = 4;
