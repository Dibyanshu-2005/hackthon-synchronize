package output

import _ "embed"

//go:embed dashboard.html
var dashboardHTMLContent string

func getDashboardHTML() string {
	return dashboardHTMLContent
}
