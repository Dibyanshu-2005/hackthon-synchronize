package generators

import (
	"math"
	"math/rand"
)

// Clamp restricts a value between min and max.
func Clamp(val, min, max float64) float64 {
	if val < min {
		return min
	}
	if val > max {
		return max
	}
	return val
}

// ClampInt restricts an integer between min and max.
func ClampInt(val, min, max int) int {
	if val < min {
		return min
	}
	if val > max {
		return max
	}
	return val
}

// Drift applies a random walk to a value within bounds.
func Drift(current, minVal, maxVal, maxDelta float64) float64 {
	delta := (rand.Float64()*2 - 1) * maxDelta
	return Clamp(current+delta, minVal, maxVal)
}

// DriftInt applies a random walk to an integer within bounds.
func DriftInt(current, minVal, maxVal, maxDelta int) int {
	delta := rand.Intn(maxDelta*2+1) - maxDelta
	return ClampInt(current+delta, minVal, maxVal)
}

// RoundTo rounds a float to n decimal places.
func RoundTo(val float64, places int) float64 {
	pow := math.Pow(10, float64(places))
	return math.Round(val*pow) / pow
}

// RandomChoice picks a random element from a slice.
func RandomChoice[T any](choices []T) T {
	return choices[rand.Intn(len(choices))]
}

// WeightedChoice picks based on weights. weights must sum > 0.
func WeightedChoice[T any](choices []T, weights []float64) T {
	total := 0.0
	for _, w := range weights {
		total += w
	}
	r := rand.Float64() * total
	cumulative := 0.0
	for i, w := range weights {
		cumulative += w
		if r <= cumulative {
			return choices[i]
		}
	}
	return choices[len(choices)-1]
}

// Chance returns true with the given probability (0.0-1.0).
func Chance(probability float64) bool {
	return rand.Float64() < probability
}

// GaussianDrift applies gaussian-distributed drift for more natural variation.
func GaussianDrift(current, minVal, maxVal, stddev float64) float64 {
	delta := rand.NormFloat64() * stddev
	return Clamp(current+delta, minVal, maxVal)
}
