#include "PluginEditor.h"

VstAiDemoAudioProcessorEditor::VstAiDemoAudioProcessorEditor(VstAiDemoAudioProcessor& processor)
    : juce::AudioProcessorEditor(&processor)
{
    // Title
    titleLabel.setText("VstAiDemo Reverb", juce::dontSendNotification);
    titleLabel.setJustificationType(juce::Justification::centred);
    titleLabel.setFont(juce::Font(24.0f, juce::Font::bold));
    addAndMakeVisible(titleLabel);

    // Mix Label
    mixLabel.setText("Wet/Dry Mix", juce::dontSendNotification);
    mixLabel.setJustificationType(juce::Justification::centred);
    mixLabel.setFont(juce::Font(14.0f));
    addAndMakeVisible(mixLabel);

    // Mix Slider
    mixSlider.setSliderStyle(juce::Slider::Rotary);
    mixSlider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 60, 20);
    mixSlider.setRange(0.0, 1.0, 0.01);
    addAndMakeVisible(mixSlider);
    mixAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        processor.apvts, "mix", mixSlider);

    // Decay Label
    decayLabel.setText("Decay Time", juce::dontSendNotification);
    decayLabel.setJustificationType(juce::Justification::centred);
    decayLabel.setFont(juce::Font(14.0f));
    addAndMakeVisible(decayLabel);

    // Decay Slider
    decaySlider.setSliderStyle(juce::Slider::Rotary);
    decaySlider.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 60, 20);
    decaySlider.setRange(0.1, 2.0, 0.01);
    addAndMakeVisible(decaySlider);
    decayAttachment = std::make_unique<juce::AudioProcessorValueTreeState::SliderAttachment>(
        processor.apvts, "decay", decaySlider);

    setSize(500, 280);
}

void VstAiDemoAudioProcessorEditor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colours::darkgrey);
}

void VstAiDemoAudioProcessorEditor::resized()
{
    auto area = getLocalBounds();
    
    // Title at top
    titleLabel.setBounds(area.removeFromTop(60));
    
    // Spacing
    area.removeFromTop(20);
    
    // Create two columns for the knobs
    auto leftColumn = area.removeFromLeft(area.getWidth() / 2);
    auto rightColumn = area;
    
    // Left column: Mix knob
    auto mixArea = leftColumn.reduced(10);
    mixLabel.setBounds(mixArea.removeFromTop(30));
    mixArea.removeFromTop(10);
    mixSlider.setBounds(mixArea.reduced(20));
    
    // Right column: Decay knob
    auto decayArea = rightColumn.reduced(10);
    decayLabel.setBounds(decayArea.removeFromTop(30));
    decayArea.removeFromTop(10);
    decaySlider.setBounds(decayArea.reduced(20));
}
